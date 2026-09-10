package util

import "time"

var beijingLocation = time.FixedZone("CST", 8*3600)

// UTCNow returns the current time in UTC truncated or rounded cleanly.
func UTCNow() time.Time {
	return time.Now().UTC()
}

// ToBeijing converts a time.Time to Beijing (UTC+8) time zone.
func ToBeijing(t time.Time) time.Time {
	return t.In(beijingLocation)
}

// BeijingNow returns the current time in Beijing (UTC+8) time zone.
func BeijingNow() time.Time {
	return time.Now().In(beijingLocation)
}
