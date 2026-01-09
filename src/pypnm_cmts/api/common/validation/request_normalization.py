# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pypnm.lib.types import ChannelId, MacAddressStr

from pypnm_cmts.lib.types import ServiceGroupId


class RequestListNormalizer:
    """
    Shared request-list normalization helpers for CMTS models.
    """

    @staticmethod
    def dedupe_int_preserve_order(values: list[int] | None) -> list[int] | None:
        """
        De-duplicate integer lists while preserving first-seen order.
        """
        if values is None:
            return None
        if not values:
            return values
        seen: set[int] = set()
        ordered: list[int] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    @staticmethod
    def assert_unique_int_preserve_order(values: list[int] | None, label: str) -> list[int] | None:
        """
        Reject duplicate integers while preserving first-seen order.
        """
        if values is None:
            return None
        if not values:
            return values
        seen: set[int] = set()
        duplicates: list[int] = []
        for value in values:
            if value in seen:
                duplicates.append(value)
                continue
            seen.add(value)
        if duplicates:
            dup_list = ", ".join(str(value) for value in duplicates)
            raise ValueError(f"{label} contains duplicate values: {dup_list}")
        return values

    @staticmethod
    def dedupe_channel_ids(values: list[ChannelId] | None) -> list[ChannelId] | None:
        """
        De-duplicate ChannelId lists while preserving first-seen order.
        """
        if values is None:
            return None
        if not values:
            return values
        seen: set[int] = set()
        ordered: list[ChannelId] = []
        for channel_id in values:
            key = int(channel_id)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(channel_id)
        return ordered

    @staticmethod
    def assert_unique_channel_ids(values: list[ChannelId] | None, label: str) -> list[ChannelId] | None:
        """
        Reject duplicate ChannelId values while preserving first-seen order.
        """
        if values is None:
            return None
        if not values:
            return values
        seen: set[int] = set()
        duplicates: list[int] = []
        for channel_id in values:
            key = int(channel_id)
            if key in seen:
                duplicates.append(key)
                continue
            seen.add(key)
        if duplicates:
            dup_list = ", ".join(str(value) for value in duplicates)
            raise ValueError(f"{label} contains duplicate values: {dup_list}")
        return values

    @staticmethod
    def dedupe_service_group_ids(values: list[ServiceGroupId]) -> list[ServiceGroupId]:
        """
        De-duplicate service group ids and preserve existing sorted behavior.
        """
        if not values:
            return values
        unique = {int(sg_id): sg_id for sg_id in values}
        return [unique[key] for key in sorted(unique.keys())]

    @staticmethod
    def assert_unique_service_group_ids(values: list[ServiceGroupId], label: str) -> list[ServiceGroupId]:
        """
        Reject duplicate service group ids while preserving input order.
        """
        if not values:
            return values
        seen: set[int] = set()
        duplicates: list[int] = []
        for sg_id in values:
            key = int(sg_id)
            if key in seen:
                duplicates.append(key)
                continue
            seen.add(key)
        if duplicates:
            dup_list = ", ".join(str(value) for value in duplicates)
            raise ValueError(f"{label} contains duplicate values: {dup_list}")
        return values

    @staticmethod
    def dedupe_mac_addresses(values: list[MacAddressStr]) -> list[MacAddressStr]:
        """
        De-duplicate MAC addresses while preserving first-seen order.
        """
        if not values:
            return values
        seen: set[str] = set()
        ordered: list[MacAddressStr] = []
        for mac in values:
            mac_str = str(mac)
            if mac_str in seen:
                continue
            seen.add(mac_str)
            ordered.append(mac)
        return ordered

    @staticmethod
    def assert_unique_mac_addresses(values: list[MacAddressStr], label: str) -> list[MacAddressStr]:
        """
        Reject duplicate MAC addresses while preserving input order.
        """
        if not values:
            return values
        seen: set[str] = set()
        duplicates: list[str] = []
        for mac in values:
            mac_str = str(mac)
            if mac_str in seen:
                duplicates.append(mac_str)
                continue
            seen.add(mac_str)
        if duplicates:
            dup_list = ", ".join(duplicates)
            raise ValueError(f"{label} contains duplicate values: {dup_list}")
        return values
