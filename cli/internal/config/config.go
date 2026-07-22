package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const (
	EnvServerURL      = "ORBYTE_SERVER_URL"
	EnvAPIKey         = "ORBYTE_PAT"
	EnvAgentID        = "ORBYTE_PERSONA_ID"
	EnvSSHHostKey     = "ORBYTE_SSH_HOST_KEY"
	EnvStreamMarkdown = "ORBYTE_STREAM_MARKDOWN"
)

// Features holds experimental feature flags for the CLI.
type Features struct {
	// StreamMarkdown enables progressive markdown rendering during streaming,
	// so output is formatted as it arrives rather than after completion.
	// nil means use the app default (true).
	StreamMarkdown *bool `json:"stream_markdown,omitempty"`
}

// OrbyteCliConfig holds the CLI configuration.
type OrbyteCliConfig struct {
	ServerURL      string   `json:"server_url"`
	APIKey         string   `json:"api_key"`
	DefaultAgentID int      `json:"default_persona_id"`
	Features       Features `json:"features,omitempty"`
}

// DefaultConfig returns a config with default values.
func DefaultConfig() OrbyteCliConfig {
	return OrbyteCliConfig{
		ServerURL:      "https://cloud.onyx.app",
		APIKey:         "",
		DefaultAgentID: 0,
	}
}

// StreamMarkdownEnabled returns whether stream markdown is enabled,
// defaulting to true when the user hasn't set an explicit preference.
func (f Features) StreamMarkdownEnabled() bool {
	if f.StreamMarkdown != nil {
		return *f.StreamMarkdown
	}
	return true
}

// IsConfigured returns true if the config has a personal access token (PAT).
func (c OrbyteCliConfig) IsConfigured() bool {
	return c.APIKey != ""
}

// APIURL appends the API prefix (default "/api") to the server origin.
// Set ORBYTE_API_PREFIX="" for direct backend access without the proxy prefix.
func APIURL(serverURL string) string {
	prefix := "/api"
	if v, ok := os.LookupEnv("ORBYTE_API_PREFIX"); ok {
		prefix = v
	}
	u := strings.TrimRight(serverURL, "/")
	if prefix == "" {
		return u
	}
	return u + "/" + strings.Trim(prefix, "/")
}

// ConfigDir returns ~/.config/orbyte-cli
func ConfigDir() string {
	if xdg := os.Getenv("XDG_CONFIG_HOME"); xdg != "" {
		return filepath.Join(xdg, "orbyte-cli")
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return filepath.Join(".", ".config", "orbyte-cli")
	}
	return filepath.Join(home, ".config", "orbyte-cli")
}

// ConfigFilePath returns the full path to the config file.
func ConfigFilePath() string {
	return filepath.Join(ConfigDir(), "config.json")
}

// ConfigExists checks if the config file exists on disk.
func ConfigExists() bool {
	_, err := os.Stat(ConfigFilePath())
	return err == nil
}

// LoadFromDisk reads config from the file only, without applying environment
// variable overrides. Use this when you need the persisted config values
// (e.g., to preserve them during a save operation).
func LoadFromDisk() OrbyteCliConfig {
	cfg := DefaultConfig()

	data, err := os.ReadFile(ConfigFilePath())
	if err == nil {
		if jsonErr := json.Unmarshal(data, &cfg); jsonErr != nil {
			fmt.Fprintf(os.Stderr, "warning: config file %s is malformed: %v (using defaults)\n", ConfigFilePath(), jsonErr)
		}
	}

	return cfg
}

// Load reads config from file and applies environment variable overrides.
func Load() OrbyteCliConfig {
	cfg := LoadFromDisk()

	// Environment overrides
	if v := os.Getenv(EnvServerURL); v != "" {
		cfg.ServerURL = v
	}
	if v := os.Getenv(EnvAPIKey); v != "" {
		cfg.APIKey = v
	}
	if v := os.Getenv(EnvAgentID); v != "" {
		if id, err := strconv.Atoi(v); err == nil {
			cfg.DefaultAgentID = id
		}
	}
	if v := os.Getenv(EnvStreamMarkdown); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			cfg.Features.StreamMarkdown = &b
		} else {
			fmt.Fprintf(os.Stderr, "warning: invalid value %q for %s (expected true/false), ignoring\n", v, EnvStreamMarkdown)
		}
	}

	return cfg
}

// Save writes the config to disk, creating parent directories if needed.
func Save(cfg OrbyteCliConfig) error {
	dir := ConfigDir()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(ConfigFilePath(), data, 0o600)
}
