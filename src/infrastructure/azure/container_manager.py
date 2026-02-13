import structlog
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import ContainerGroup

from src.config import settings

logger = structlog.get_logger(__name__)


class ContainerManagerError(Exception):
    """Raised when container operations fail."""
    pass


class AzureContainerManager:

    def __init__(
        self,
        subscription_id: str = settings.azure_subscription_id,
        resource_group: str = settings.azure_resource_group,
    ) -> None:
        if not subscription_id:
            raise ContainerManagerError("AZURE_SUBSCRIPTION_ID not configured")
        
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.credential = DefaultAzureCredential()
        self.client = ContainerInstanceManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

    async def start_container(self, container_name: str) -> None:

        try:
            logger.info("starting_container", container=container_name, rg=self.resource_group)
            container_groups = self.client.container_groups
            if hasattr(container_groups, "begin_start"):
                container_groups.begin_start(self.resource_group, container_name).result()
            elif hasattr(container_groups, "start"):
                container_groups.start(self.resource_group, container_name)
            else:
                raise ContainerManagerError("Container group start operation is not available in this SDK version")
            logger.info("container_started", container=container_name)
        except Exception as exc:
            logger.error(
                "failed_to_start_container",
                container=container_name,
                error=str(exc),
            )
            raise ContainerManagerError(f"Failed to start container {container_name}: {exc}")

    async def stop_container(self, container_name: str) -> None:

        try:
            logger.info("stopping_container", container=container_name, rg=self.resource_group)
            self.client.container_groups.stop(self.resource_group, container_name)
            logger.info("container_stopped", container=container_name)
        except Exception as exc:
            logger.error(
                "failed_to_stop_container",
                container=container_name,
                error=str(exc),
            )
            raise ContainerManagerError(f"Failed to stop container {container_name}: {exc}")

    def get_container_status(self, container_name: str) -> str:

        try:
            container: ContainerGroup = self.client.container_groups.get(
                self.resource_group,
                container_name,
            )
            if container.instance_view and container.instance_view.state:
                return container.instance_view.state
            return "Unknown"
        except Exception as exc:
            logger.error(
                "failed_to_get_container_status",
                container=container_name,
                error=str(exc),
            )
            return "Unknown"
