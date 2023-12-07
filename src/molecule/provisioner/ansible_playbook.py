#  Copyright (c) 2015-2018 Cisco Systems, Inc.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
"""Distronode-Playbook Provisioner Module."""

import logging
import shlex
import warnings

from molecule import util
from molecule.api import MoleculeRuntimeWarning

LOG = logging.getLogger(__name__)


class DistronodePlaybook:
    """Provisioner Playbook."""

    def __init__(self, playbook, config, verify=False) -> None:
        """Set up the requirements to execute ``distronode-playbook`` and returns \
        None.

        :param playbook: A string containing the path to the playbook.
        :param config: An instance of a Molecule config.
        :param verify: An optional bool to toggle the Plabook mode between
         provision and verify. False: provision; True: verify. Default is False.
        :returns: None
        """
        self._distronode_command = None
        self._playbook = playbook
        self._config = config
        self._cli = {}  # type: ignore
        if verify:
            self._env = util.merge_dicts(
                self._config.verifier.env,
                self._config.config["verifier"]["env"],
            )
        else:
            self._env = self._config.provisioner.env

    def bake(self):
        """Bake an ``distronode-playbook`` command so it's ready to execute and \
        returns ``None``.

        :return: None
        """
        if not self._playbook:
            return

        # Pass a directory as inventory to let Distronode merge the multiple
        # inventory sources located under
        self.add_cli_arg("inventory", self._config.provisioner.inventory_directory)
        options = util.merge_dicts(self._config.provisioner.options, self._cli)
        verbose_flag = util.verbose_flag(options)
        if self._playbook != self._config.provisioner.playbooks.converge:
            if options.get("become"):
                del options["become"]

        # We do not pass user-specified Distronode arguments to the create and
        # destroy invocations because playbooks involved in those two
        # operations are not always provided by end users. And in those cases,
        # custom Distronode arguments can break the creation and destruction
        # processes.
        #
        # If users need to modify the creation of deletion, they can supply
        # custom playbooks and specify them in the scenario configuration.
        if self._config.action not in ["create", "destroy"]:
            distronode_args = list(self._config.provisioner.distronode_args) + list(
                self._config.distronode_args,
            )
        else:
            distronode_args = []

        self._distronode_command = [
            "distronode-playbook",
            *util.dict2args(options),
            *util.bool2args(verbose_flag),
            *distronode_args,
            self._playbook,  # must always go last
        ]

    def execute(self, action_args=None):
        """Execute ``distronode-playbook`` and returns a string.

        :return: str
        """
        if self._distronode_command is None:
            self.bake()

        if not self._playbook:
            LOG.warning("Skipping, %s action has no playbook.", self._config.action)
            return None

        with warnings.catch_warnings(record=True) as warns:
            warnings.filterwarnings("default", category=MoleculeRuntimeWarning)
            self._config.driver.sanity_checks()
            cwd = self._config.scenario_path
            result = util.run_command(
                cmd=self._distronode_command,
                env=self._env,
                debug=self._config.debug,
                cwd=cwd,
            )

        if result.returncode != 0:
            from rich.markup import escape

            util.sysexit_with_message(
                f"Distronode return code was {result.returncode}, command was: [dim]{escape(shlex.join(result.args))}[/dim]",
                result.returncode,
                warns=warns,
            )

        return result.stdout

    def add_cli_arg(self, name, value):
        """Add argument to CLI passed to distronode-playbook and returns None.

        :param name: A string containing the name of argument to be added.
        :param value: The value of argument to be added.
        :return: None
        """
        if value:
            self._cli[name] = value

    def add_env_arg(self, name, value):
        """Add argument to environment passed to distronode-playbook and returns \
        None.

        :param name: A string containing the name of argument to be added.
        :param value: The value of argument to be added.
        :return: None
        """
        self._env[name] = value