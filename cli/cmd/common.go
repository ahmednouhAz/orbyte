package cmd

import (
	"errors"

	"github.com/orbyte-dot-app/orbyte/cli/internal/api"
	"github.com/orbyte-dot-app/orbyte/cli/internal/config"
	"github.com/orbyte-dot-app/orbyte/cli/internal/exitcodes"
)

func requireConfig() (config.OrbyteCliConfig, error) {
	cfg := config.Load()
	if !cfg.IsConfigured() {
		return cfg, exitcodes.New(exitcodes.NotConfigured,
			"orbyte CLI is not configured\n  Set ORBYTE_PAT (and optionally ORBYTE_SERVER_URL), or run: orbyte-cli chat to complete first-time setup")
	}
	return cfg, nil
}

func requireClient() (config.OrbyteCliConfig, *api.Client, error) {
	cfg, err := requireConfig()
	if err != nil {
		return cfg, nil, err
	}
	return cfg, api.NewClient(cfg), nil
}

func apiErrorToExit(err error, action string) error {
	var authErr *api.AuthError
	if errors.As(err, &authErr) {
		return exitcodes.Newf(exitcodes.AuthFailure, "%s: %v", action, err)
	}
	var apiErr *api.OrbyteAPIError
	if errors.As(err, &apiErr) {
		return exitcodes.Newf(exitcodes.ForHTTPStatus(apiErr.StatusCode), "%s: %s", action, apiErr.Error())
	}
	return exitcodes.Newf(exitcodes.Unreachable, "%s: %v", action, err)
}
