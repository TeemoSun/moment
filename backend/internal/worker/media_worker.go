package worker

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
)

type MediaJob struct {
	MediaID int
	Kind    string
}

type MediaWorkerPool struct {
	cfg     *config.Config
	repos   *repository.Repositories
	queue   chan MediaJob
	workers int
	wg      sync.WaitGroup
	ctx     context.Context
	cancel  context.CancelFunc
}

func NewMediaWorkerPool(cfg *config.Config, repos *repository.Repositories, numWorkers int) *MediaWorkerPool {
	ctx, cancel := context.WithCancel(context.Background())
	return &MediaWorkerPool{
		cfg:     cfg,
		repos:   repos,
		queue:   make(chan MediaJob, 500),
		workers: numWorkers,
		ctx:     ctx,
		cancel:  cancel,
	}
}

func (p *MediaWorkerPool) Start() {
	for i := 0; i < p.workers; i++ {
		p.wg.Add(1)
		go p.workerLoop(i)
	}
}

func (p *MediaWorkerPool) Stop() {
	p.cancel()
	close(p.queue)
	p.wg.Wait()
}

func (p *MediaWorkerPool) Submit(mediaID int, kind string) {
	select {
	case p.queue <- MediaJob{MediaID: mediaID, Kind: kind}:
	default:
		log.Printf("[MediaWorker] warning: queue full, dropping media processing %d", mediaID)
	}
}

func (p *MediaWorkerPool) workerLoop(workerID int) {
	defer p.wg.Done()
	for job := range p.queue {
		if job.Kind == "image" {
			p.processImage(job.MediaID)
		} else if job.Kind == "video" {
			p.processVideo(job.MediaID)
		}
	}
}

func (p *MediaWorkerPool) processImage(mediaID int) {
	ctx := context.Background()
	media, err := p.repos.Media.GetMediaByID(ctx, mediaID)
	if err != nil || media == nil {
		return
	}

	srcAbs := filepath.Join(p.cfg.StorageRoot, media.FilePath)
	if _, err := os.Stat(srcAbs); err != nil {
		return
	}

	stem := strings.TrimSuffix(media.Filename, filepath.Ext(media.Filename))
	dir := filepath.Dir(srcAbs)

	thumbName := fmt.Sprintf("%s_thumb.webp", stem)
	largeName := fmt.Sprintf("%s_large.webp", stem)
	thumbAbs := filepath.Join(dir, thumbName)
	largeAbs := filepath.Join(dir, largeName)

	// Thumbnail
	cmdThumb := exec.Command("ffmpeg", "-y", "-i", srcAbs,
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", p.cfg.ThumbSize),
		"-quality", fmt.Sprintf("%d", p.cfg.WebpThumbQuality),
		thumbAbs)
	if err := cmdThumb.Run(); err != nil {
		log.Printf("[MediaWorker] ffmpeg thumb error on media %d: %v", mediaID, err)
	}

	// Large
	cmdLarge := exec.Command("ffmpeg", "-y", "-i", srcAbs,
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", p.cfg.LargeSize),
		"-quality", fmt.Sprintf("%d", p.cfg.WebpLargeQuality),
		largeAbs)
	if err := cmdLarge.Run(); err != nil {
		log.Printf("[MediaWorker] ffmpeg large error on media %d: %v", mediaID, err)
	}

	thumbRel, err := filepath.Rel(p.cfg.StorageRoot, thumbAbs)
	if err != nil {
		thumbRel = thumbAbs
	}
	largeRel, err := filepath.Rel(p.cfg.StorageRoot, largeAbs)
	if err != nil {
		largeRel = largeAbs
	}

	_ = p.repos.Media.UpdateMediaPaths(ctx, mediaID, &thumbRel, &largeRel)

	if fi, err := os.Stat(thumbAbs); err == nil {
		_ = p.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
			StoragePath:  thumbRel,
			OriginalName: media.Filename,
			Filename:     thumbName,
			Size:         int(fi.Size()),
			Mime:         "image/webp",
			Format:       "webp",
			Kind:         "thumb",
			OwnerID:      media.OwnerID,
		})
	}

	if fi, err := os.Stat(largeAbs); err == nil {
		_ = p.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
			StoragePath:  largeRel,
			OriginalName: media.Filename,
			Filename:     largeName,
			Size:         int(fi.Size()),
			Mime:         "image/webp",
			Format:       "webp",
			Kind:         "large",
			OwnerID:      media.OwnerID,
		})
	}
}

func (p *MediaWorkerPool) processVideo(mediaID int) {
	ctx := context.Background()
	media, err := p.repos.Media.GetMediaByID(ctx, mediaID)
	if err != nil || media == nil {
		return
	}

	srcAbs := filepath.Join(p.cfg.StorageRoot, media.FilePath)
	if _, err := os.Stat(srcAbs); err != nil {
		return
	}

	stem := strings.TrimSuffix(media.Filename, filepath.Ext(media.Filename))
	dir := filepath.Dir(srcAbs)

	thumbName := fmt.Sprintf("%s_thumb.webp", stem)
	thumbAbs := filepath.Join(dir, thumbName)

	// First frame -> thumbnail webp
	cmd := exec.Command("ffmpeg", "-y", "-i", srcAbs,
		"-vframes", "1",
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", p.cfg.ThumbSize),
		thumbAbs)
	if err := cmd.Run(); err != nil {
		log.Printf("[MediaWorker] ffmpeg video frame extraction error on media %d: %v", mediaID, err)
		return
	}

	if _, err := os.Stat(thumbAbs); err == nil {
		thumbRel, _ := filepath.Rel(p.cfg.StorageRoot, thumbAbs)
		_ = p.repos.Media.UpdateMediaPaths(ctx, mediaID, &thumbRel, nil)

		fi, _ := os.Stat(thumbAbs)
		_ = p.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
			StoragePath:  thumbRel,
			OriginalName: media.Filename,
			Filename:     thumbName,
			Size:         int(fi.Size()),
			Mime:         "image/webp",
			Format:       "webp",
			Kind:         "thumb",
			OwnerID:      media.OwnerID,
		})
	}
}
