package api

import "fmt"

// OrbyteAPIError is returned when an Orbyte API call fails.
type OrbyteAPIError struct {
	StatusCode int
	Detail     string
}

func (e *OrbyteAPIError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.StatusCode, e.Detail)
}

// AuthError is returned when authentication or authorization fails.
type AuthError struct {
	Message string
}

func (e *AuthError) Error() string {
	return e.Message
}
