"""Main client generator orchestrator."""

import shutil
from pathlib import Path
from typing import cast

import humps

from chanx.asyncapi.type_defs import AsyncAPIDocument, ChannelObject, MessageObject
from chanx.client_generator.analyzer import SharedItemsAnalyzer
from chanx.client_generator.codegen import (
    extract_channel_messages,
    extract_schemas_from_messages,
    generate_pydantic_code,
    topological_sort_schemas,
)
from chanx.client_generator.loader import SchemaLoader
from chanx.client_generator.templates import (
    CHANNEL_CLIENT_TEMPLATE,
    CHANNEL_INIT_TEMPLATE,
    DEMULTIPLEXER_CLIENT_TEMPLATE,
    PACKAGE_INIT_TEMPLATE,
    README_TEMPLATE,
    SUB_CLIENT_TEMPLATE,
    get_template,
)


class ClientGenerator:
    """
    Generate WebSocket client code from AsyncAPI schema.

    This orchestrates the entire generation process:
    1. Load schema from file
    2. Parse and validate schema
    3. Analyze dependencies (shared vs channel-specific)
    4. Generate code files
    5. Write output
    """

    def __init__(
        self,
        schema_path: str,
        output_dir: str,
        generate_readme: bool = True,
        clear_output: bool = False,
        override_base: bool = False,
        clear_channels: bool = True,
    ):
        """
        Initialize client generator.

        Args:
            schema_path: Path to AsyncAPI schema file
            output_dir: Output directory for generated code
            generate_readme: Whether to generate README.md file
            clear_output: Whether to remove entire output directory before generation
            override_base: Whether to regenerate base files even if they exist
            clear_channels: Whether to clear channel folders (except base) before generation
        """
        self.schema_path = schema_path
        self.output_dir = Path(output_dir)
        self.generate_readme = generate_readme
        self.clear_output = clear_output
        self.override_base = override_base
        self.clear_channels = clear_channels

        # Load and parse schema
        schema_dict = SchemaLoader.load(schema_path)
        self.schema = AsyncAPIDocument.model_validate(schema_dict)

        self.channel_messages = extract_channel_messages(self.schema)

        # Initialize analyzer
        shared_item_analyzer = SharedItemsAnalyzer(self.schema)
        self.shared_messages = shared_item_analyzer.shared_messages
        self.shared_schemas = shared_item_analyzer.shared_schemas

        # Initialize code generator
        self.client_generator_path = Path(__file__).parent

    def generate(self) -> None:
        """Generate complete client package."""
        # Create output directory structure
        self._create_directory_structure()

        # Generate base client
        self._generate_base()

        if self.shared_schemas:
            self._generate_shared_schemas()

        # Generate channel clients
        self._generate_channel_clients()

        # Generate main __init__.py
        self._generate_init()

        # Generate README.md
        if self.generate_readme:
            self._generate_readme()

    def _create_directory_structure(self) -> None:
        """Create output directory structure."""
        if self.output_dir.exists():
            if self.clear_output:
                # Remove entire directory
                shutil.rmtree(self.output_dir)
            elif self.clear_channels:
                # Remove everything except base folder
                for item in self.output_dir.iterdir():
                    if item.name != "base":
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create shared directory if needed
        if self.shared_schemas:
            (self.output_dir / "shared").mkdir(exist_ok=True)

        # Create directory for each channel
        assert self.schema.channels
        for channel in self.schema.channels.values():
            (self.output_dir / channel.title).mkdir(exist_ok=True)

    def _generate_base(self) -> None:
        """Generate base client class."""
        source_base_dir = self.client_generator_path / "base"
        target_base_dir = self.output_dir / "base"

        # Only regenerate base if it doesn't exist or override_base is True
        if self.override_base or not target_base_dir.exists():
            shutil.copytree(source_base_dir, target_base_dir, dirs_exist_ok=True)

    def _generate_shared_schemas(self) -> None:
        """Generate shared message schemas used across multiple channels."""
        # Generate code
        sorted_schema = topological_sort_schemas(self.shared_schemas)
        code = generate_pydantic_code(sorted_schema)

        # Write file
        output_path = self.output_dir / "shared" / "messages.py"
        output_path.write_text(code, encoding="utf-8")

        # Create __init__.py in shared
        init_path = self.output_dir / "shared" / "__init__.py"
        init_path.touch()

    def _generate_channel_clients(self) -> None:
        """Generate client classes for each channel."""
        sub_clients_by_demultiplexer = self._group_multiplexed_channels()

        for channel in self.schema.channels.values():
            # Generate message models and collect exported names
            assert channel.messages
            channel_messages = cast(list[MessageObject], channel.messages.values())
            message_exports = self._generate_channel_messages(channel, channel_messages)

            code = self._render_channel_client(
                channel,
                has_outgoing="OutgoingMessage" in message_exports,
                sub_clients=sub_clients_by_demultiplexer.get(channel.title, []),
            )

            # Write client file
            output_path = self.output_dir / channel.title / "client.py"
            output_path.write_text(code, encoding="utf-8")

            # Create __init__.py
            self._generate_channel_init(channel.title, message_exports)

    def _group_multiplexed_channels(self) -> dict[str, list[dict[str, str]]]:
        """
        Map each demultiplexer channel to the sub-clients it serves.

        Channels of one multiplexed route share an address, and exactly one of
        them -- the demultiplexer's -- has no consumer key. That is what ties a
        group together.

        Returns:
            Dict mapping demultiplexer channel title to its sub-client descriptors
        """
        assert self.schema.channels
        multiplexed = [c for c in self.schema.channels.values() if c.multiplex]

        demultiplexer_titles = {
            channel.address: channel.title
            for channel in multiplexed
            if channel.multiplex and channel.multiplex.consumerKey is None
        }

        groups: dict[str, list[dict[str, str]]] = {
            title: [] for title in demultiplexer_titles.values()
        }
        for channel in multiplexed:
            assert channel.multiplex
            consumer_key = channel.multiplex.consumerKey
            if consumer_key is None:
                continue

            title = demultiplexer_titles.get(channel.address)
            if title is None:
                # No demultiplexer channel documented at this address; nothing can
                # connect the sub-client, so leave it out rather than emit a client
                # that cannot be reached.
                continue

            groups[title].append(
                {
                    "consumer_key": consumer_key,
                    "module": channel.title,
                    "class_name": humps.pascalize(channel.title) + "Client",
                }
            )

        return groups

    def _render_channel_client(
        self,
        channel: ChannelObject,
        has_outgoing: bool,
        sub_clients: list[dict[str, str]],
    ) -> str:
        """
        Render the client class for one channel.

        A multiplexed route produces two kinds: a demultiplexer client owning the
        socket, and one sub-client per consumer that borrows it.

        Args:
            channel: The channel to render a client for
            has_outgoing: Whether the channel's messages module defines OutgoingMessage
            sub_clients: Sub-client descriptors, for a demultiplexer channel

        Returns:
            The rendered client module source
        """
        class_name = humps.pascalize(channel.title) + "Client"
        common = {
            "channel_title": channel.title,
            "channel_description": channel.description,
            "channel_address": channel.address,
            "class_name": class_name,
            "has_outgoing": has_outgoing,
        }

        extension = channel.multiplex
        if extension is None:
            return get_template(CHANNEL_CLIENT_TEMPLATE).render(
                **common,
                path_params=(
                    list(channel.parameters.keys()) if channel.parameters else None
                ),
            )

        if extension.consumerKey is not None:
            return get_template(SUB_CLIENT_TEMPLATE).render(
                **common, consumer_key=extension.consumerKey
            )

        return get_template(DEMULTIPLEXER_CLIENT_TEMPLATE).render(
            **common,
            consumer_field=extension.consumerField,
            message_field=extension.messageField,
            version_field=extension.versionField,
            envelope_version=extension.version,
            sub_clients=sub_clients,
        )

    def _generate_channel_messages(
        self, channel: ChannelObject, messages: list[MessageObject]
    ) -> list[str]:
        """Generate message models for a specific channel.

        Returns:
            List of exported class names from this channel's messages
        """
        # Extract and generate schemas
        schemas = extract_schemas_from_messages(messages)
        code = generate_pydantic_code(schemas, self.shared_schemas)

        # Collect all class names that will be exported (only local, non-shared)
        exported_classes: list[str] = []
        shared_schema_set = cast(
            set[str],
            {s.title for s in self.shared_schemas} if self.shared_schemas else set(),
        )
        for schema in schemas:
            if schema.title and schema.title not in shared_schema_set:
                exported_classes.append(schema.title)

        # Generate message union types
        incoming_messages, outgoing_messages = self.channel_messages.get(
            channel.title, ([], [])
        )
        incoming_messages = self._with_operationless_messages(
            channel, messages, incoming_messages, outgoing_messages
        )

        lines: list[str] = []
        if incoming_messages:
            incoming_titles = list(
                dict.fromkeys(
                    m.payload.title
                    for m in incoming_messages
                    if m.payload and m.payload.title
                )
            )
            lines.append(f"IncomingMessage = {' | '.join(incoming_titles)}")
            exported_classes.append("IncomingMessage")

        if outgoing_messages:
            outgoing_titles = list(
                dict.fromkeys(
                    m.payload.title
                    for m in outgoing_messages
                    if m.payload and m.payload.title
                )
            )
            lines.append(f"OutgoingMessage = {' | '.join(outgoing_titles)}")
            exported_classes.append("OutgoingMessage")

        if lines:
            code = code + "\n".join(lines) + "\n"

        # Write messages file
        output_path = self.output_dir / channel.title / "messages.py"
        output_path.write_text(code, encoding="utf-8")

        return exported_classes

    @staticmethod
    def _with_operationless_messages(
        channel: ChannelObject,
        messages: list[MessageObject],
        incoming: list[MessageObject],
        outgoing: list[MessageObject],
    ) -> list[MessageObject]:
        """
        Count a demultiplexer channel's handler-less messages as incoming.

        Incoming and outgoing are otherwise derived from operations, and the
        multiplex_ready handshake has no operation: no handler produces it. A
        demultiplexer that declares no top-level handlers would end up with no
        IncomingMessage at all, and its client would have nothing to validate
        against. A message a client cannot send can only be one it receives.

        Args:
            channel: The channel the messages belong to
            messages: Every message documented on the channel
            incoming: Messages already known to be incoming
            outgoing: Messages already known to be outgoing

        Returns:
            The incoming list, extended for a demultiplexer channel
        """
        if channel.multiplex is None or channel.multiplex.consumerKey is not None:
            return incoming

        known = {id(message) for message in incoming + outgoing}
        return incoming + [m for m in messages if id(m) not in known]

    def _generate_channel_init(
        self, channel_name: str, message_exports: list[str]
    ) -> None:
        """Generate __init__.py for a channel module."""
        class_name = humps.pascalize(channel_name) + "Client"

        template = get_template(CHANNEL_INIT_TEMPLATE)
        content = template.render(
            channel_name=channel_name,
            class_name=class_name,
            message_exports=sorted(message_exports),
        )

        init_path = self.output_dir / channel_name / "__init__.py"
        init_path.write_text(content, encoding="utf-8")

    def _generate_init(self) -> None:
        """Generate main __init__.py."""
        # Collect all channel clients
        channel_exports = []
        for channel in self.schema.channels.values():
            class_name = humps.pascalize(channel.title) + "Client"
            channel_exports.append((channel.title, class_name))

        template = get_template(PACKAGE_INIT_TEMPLATE)
        content = template.render(
            title=self.schema.info.title,
            version=self.schema.info.version,
            channel_exports=channel_exports,
        )

        output_path = self.output_dir / "__init__.py"
        output_path.write_text(content, encoding="utf-8")

    def _generate_readme(self) -> None:
        """Generate README.md with usage examples."""
        # Collect channel information
        channel_info = {}
        first_channel = None
        first_class = None
        first_params = []

        for channel in self.schema.channels.values():
            class_name = humps.pascalize(channel.title) + "Client"
            path_params = []

            if channel.parameters:
                path_params = list(channel.parameters.keys())

            channel_info[channel.title] = {
                "class_name": class_name,
                "description": channel.description or "",
                "address": channel.address or "",
                "path_params": path_params,
            }

            # A sub-client cannot be connected on its own, so it would make a
            # misleading opening example.
            is_sub_client = (
                channel.multiplex is not None
                and channel.multiplex.consumerKey is not None
            )
            if first_channel is None and not is_sub_client:
                first_channel = channel.title
                first_class = class_name
                if channel.parameters:
                    first_params = path_params

        # Render README template
        template = get_template(README_TEMPLATE)
        content = template.render(
            title=self.schema.info.title,
            version=self.schema.info.version,
            description=self.schema.info.description or "",
            package_name=self.output_dir.name,
            channel_info=channel_info,
            first_channel=first_channel,
            first_class=first_class,
            first_params=first_params,
            has_shared=bool(self.shared_schemas),
            multiplex_groups=self._group_multiplexed_channels(),
        )

        # Write README
        output_path = self.output_dir / "README.md"
        output_path.write_text(content, encoding="utf-8")
