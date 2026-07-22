package cmd

import (
	"github.com/spf13/cobra"
)

// NewReleaseCommand creates the parent `ods release` command. Subcommands hang
// off it (e.g. `ods release opal`) and cut releases of Orbyte-published packages.
func NewReleaseCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "release",
		Short: "Cut releases of Orbyte-published packages",
		Long:  "Cut releases of Orbyte-published packages.",
	}

	cmd.AddCommand(NewReleaseOpalCommand())

	return cmd
}
