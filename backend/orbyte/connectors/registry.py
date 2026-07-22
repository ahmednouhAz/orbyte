"""Registry mapping for connector classes."""

from pydantic import BaseModel

from orbyte.configs.constants import DocumentSource


class ConnectorMapping(BaseModel):
    module_path: str
    class_name: str


# Mapping of DocumentSource to connector details for lazy loading
CONNECTOR_CLASS_MAP = {
    DocumentSource.WEB: ConnectorMapping(
        module_path="orbyte.connectors.web.connector",
        class_name="WebConnector",
    ),
    DocumentSource.FILE: ConnectorMapping(
        module_path="orbyte.connectors.file.connector",
        class_name="LocalFileConnector",
    ),
    DocumentSource.SLACK: ConnectorMapping(
        module_path="orbyte.connectors.slack.connector",
        class_name="SlackConnector",
    ),
    DocumentSource.GITHUB: ConnectorMapping(
        module_path="orbyte.connectors.github.connector",
        class_name="GithubConnector",
    ),
    DocumentSource.GMAIL: ConnectorMapping(
        module_path="orbyte.connectors.gmail.connector",
        class_name="GmailConnector",
    ),
    DocumentSource.GITLAB: ConnectorMapping(
        module_path="orbyte.connectors.gitlab.connector",
        class_name="GitlabConnector",
    ),
    DocumentSource.GITBOOK: ConnectorMapping(
        module_path="orbyte.connectors.gitbook.connector",
        class_name="GitbookConnector",
    ),
    DocumentSource.GOOGLE_DRIVE: ConnectorMapping(
        module_path="orbyte.connectors.google_drive.connector",
        class_name="GoogleDriveConnector",
    ),
    DocumentSource.BOOKSTACK: ConnectorMapping(
        module_path="orbyte.connectors.bookstack.connector",
        class_name="BookstackConnector",
    ),
    DocumentSource.OUTLINE: ConnectorMapping(
        module_path="orbyte.connectors.outline.connector",
        class_name="OutlineConnector",
    ),
    DocumentSource.CONFLUENCE: ConnectorMapping(
        module_path="orbyte.connectors.confluence.connector",
        class_name="ConfluenceConnector",
    ),
    DocumentSource.JIRA: ConnectorMapping(
        module_path="orbyte.connectors.jira.connector",
        class_name="JiraConnector",
    ),
    DocumentSource.PRODUCTBOARD: ConnectorMapping(
        module_path="orbyte.connectors.productboard.connector",
        class_name="ProductboardConnector",
    ),
    DocumentSource.SLAB: ConnectorMapping(
        module_path="orbyte.connectors.slab.connector",
        class_name="SlabConnector",
    ),
    DocumentSource.CODA: ConnectorMapping(
        module_path="orbyte.connectors.coda.connector",
        class_name="CodaConnector",
    ),
    DocumentSource.CANVAS: ConnectorMapping(
        module_path="orbyte.connectors.canvas.connector",
        class_name="CanvasConnector",
    ),
    DocumentSource.NOTION: ConnectorMapping(
        module_path="orbyte.connectors.notion.connector",
        class_name="NotionConnector",
    ),
    DocumentSource.ZULIP: ConnectorMapping(
        module_path="orbyte.connectors.zulip.connector",
        class_name="ZulipConnector",
    ),
    DocumentSource.GURU: ConnectorMapping(
        module_path="orbyte.connectors.guru.connector",
        class_name="GuruConnector",
    ),
    DocumentSource.LINEAR: ConnectorMapping(
        module_path="orbyte.connectors.linear.connector",
        class_name="LinearConnector",
    ),
    DocumentSource.HUBSPOT: ConnectorMapping(
        module_path="orbyte.connectors.hubspot.connector",
        class_name="HubSpotConnector",
    ),
    DocumentSource.DOCUMENT360: ConnectorMapping(
        module_path="orbyte.connectors.document360.connector",
        class_name="Document360Connector",
    ),
    DocumentSource.GONG: ConnectorMapping(
        module_path="orbyte.connectors.gong.connector",
        class_name="GongConnector",
    ),
    DocumentSource.GOOGLE_SITES: ConnectorMapping(
        module_path="orbyte.connectors.google_site.connector",
        class_name="GoogleSitesConnector",
    ),
    DocumentSource.ZENDESK: ConnectorMapping(
        module_path="orbyte.connectors.zendesk.connector",
        class_name="ZendeskConnector",
    ),
    DocumentSource.LOOPIO: ConnectorMapping(
        module_path="orbyte.connectors.loopio.connector",
        class_name="LoopioConnector",
    ),
    DocumentSource.DROPBOX: ConnectorMapping(
        module_path="orbyte.connectors.dropbox.connector",
        class_name="DropboxConnector",
    ),
    DocumentSource.SHAREPOINT: ConnectorMapping(
        module_path="orbyte.connectors.sharepoint.connector",
        class_name="SharepointConnector",
    ),
    DocumentSource.TEAMS: ConnectorMapping(
        module_path="orbyte.connectors.teams.connector",
        class_name="TeamsConnector",
    ),
    DocumentSource.SALESFORCE: ConnectorMapping(
        module_path="orbyte.connectors.salesforce.connector",
        class_name="SalesforceConnector",
    ),
    DocumentSource.DISCOURSE: ConnectorMapping(
        module_path="orbyte.connectors.discourse.connector",
        class_name="DiscourseConnector",
    ),
    DocumentSource.AXERO: ConnectorMapping(
        module_path="orbyte.connectors.axero.connector",
        class_name="AxeroConnector",
    ),
    DocumentSource.CLICKUP: ConnectorMapping(
        module_path="orbyte.connectors.clickup.connector",
        class_name="ClickupConnector",
    ),
    DocumentSource.MEDIAWIKI: ConnectorMapping(
        module_path="orbyte.connectors.mediawiki.wiki",
        class_name="MediaWikiConnector",
    ),
    DocumentSource.WIKIPEDIA: ConnectorMapping(
        module_path="orbyte.connectors.wikipedia.connector",
        class_name="WikipediaConnector",
    ),
    DocumentSource.ASANA: ConnectorMapping(
        module_path="orbyte.connectors.asana.connector",
        class_name="AsanaConnector",
    ),
    DocumentSource.S3: ConnectorMapping(
        module_path="orbyte.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.R2: ConnectorMapping(
        module_path="orbyte.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.GOOGLE_CLOUD_STORAGE: ConnectorMapping(
        module_path="orbyte.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.OCI_STORAGE: ConnectorMapping(
        module_path="orbyte.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.XENFORO: ConnectorMapping(
        module_path="orbyte.connectors.xenforo.connector",
        class_name="XenforoConnector",
    ),
    DocumentSource.DISCORD: ConnectorMapping(
        module_path="orbyte.connectors.discord.connector",
        class_name="DiscordConnector",
    ),
    DocumentSource.FRESHDESK: ConnectorMapping(
        module_path="orbyte.connectors.freshdesk.connector",
        class_name="FreshdeskConnector",
    ),
    DocumentSource.FIREFLIES: ConnectorMapping(
        module_path="orbyte.connectors.fireflies.connector",
        class_name="FirefliesConnector",
    ),
    DocumentSource.EGNYTE: ConnectorMapping(
        module_path="orbyte.connectors.egnyte.connector",
        class_name="EgnyteConnector",
    ),
    DocumentSource.AIRTABLE: ConnectorMapping(
        module_path="orbyte.connectors.airtable.airtable_connector",
        class_name="AirtableConnector",
    ),
    DocumentSource.HIGHSPOT: ConnectorMapping(
        module_path="orbyte.connectors.highspot.connector",
        class_name="HighspotConnector",
    ),
    DocumentSource.DRUPAL_WIKI: ConnectorMapping(
        module_path="orbyte.connectors.drupal_wiki.connector",
        class_name="DrupalWikiConnector",
    ),
    DocumentSource.IMAP: ConnectorMapping(
        module_path="orbyte.connectors.imap.connector",
        class_name="ImapConnector",
    ),
    DocumentSource.BITBUCKET: ConnectorMapping(
        module_path="orbyte.connectors.bitbucket.connector",
        class_name="BitbucketConnector",
    ),
    DocumentSource.TESTRAIL: ConnectorMapping(
        module_path="orbyte.connectors.testrail.connector",
        class_name="TestRailConnector",
    ),
    DocumentSource.BRAINTRUST: ConnectorMapping(
        module_path="orbyte.connectors.braintrust.connector",
        class_name="BraintrustConnector",
    ),
    DocumentSource.LUMAPPS: ConnectorMapping(
        module_path="orbyte.connectors.lumapps.connector",
        class_name="LumAppsConnector",
    ),
    # just for integration tests
    DocumentSource.MOCK_CONNECTOR: ConnectorMapping(
        module_path="orbyte.connectors.mock_connector.connector",
        class_name="MockConnector",
    ),
}
