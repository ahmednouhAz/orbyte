package cmd

import (
	"fmt"

	"github.com/orbyte-dot-app/orbyte/cli/internal/config"
	"github.com/orbyte-dot-app/orbyte/cli/internal/iostreams"
	"github.com/spf13/cobra"
)

func newExperimentsCmd(ios *iostreams.IOStreams) *cobra.Command {
	return &cobra.Command{
		Use:   "experiments",
		Short: "List experimental features and their status",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg := config.Load()
			fmt.Fprintln(ios.Out, config.ExperimentsText(cfg.Features))
			return nil
		},
	}
}
