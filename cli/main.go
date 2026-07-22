package main

import (
	"errors"
	"fmt"
	"os"

	"github.com/orbyte-dot-app/orbyte/cli/cmd"
	"github.com/orbyte-dot-app/orbyte/cli/internal/exitcodes"
)

var (
	version = "dev"
	commit  = "none"
)

func main() {
	cmd.Version = version
	cmd.Commit = commit

	if err := cmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		var exitErr *exitcodes.ExitError
		if errors.As(err, &exitErr) {
			os.Exit(int(exitErr.Code))
		}
		os.Exit(1)
	}
}
