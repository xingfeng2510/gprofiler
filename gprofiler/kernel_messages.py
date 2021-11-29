#
# Copyright (c) Granulate. All rights reserved.
# Licensed under the AGPL3 License. See LICENSE.md in the project root for license information.
#
from granulate_utils.linux.kernel_messages import DefaultKernelMessagesProvider, EmptyKernelMessagesProvider

from gprofiler.log import get_logger_adapter

logger = get_logger_adapter(__name__)


class GProfilerKernelMessagesProvider(DefaultKernelMessagesProvider):
    def on_missed(self):
        logger.warning("Missed some kernel messages.")


def get_kernel_messages_provider():
    if DefaultKernelMessagesProvider is EmptyKernelMessagesProvider:
        logger.info("Profilee error monitoring is not supported for this system.")
        return DefaultKernelMessagesProvider()

    try:
        return GProfilerKernelMessagesProvider()
    except Exception:
        logger.warning(
            "Failed to start kernel messages listener. Profilee error monitoring not available. (Do you have permission"
            " to read /dev/kmsg?)",
            exc_info=True,
        )
        return EmptyKernelMessagesProvider()