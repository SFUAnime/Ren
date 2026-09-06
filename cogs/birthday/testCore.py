import dataclasses
from datetime import datetime
import time
from typing import Any, Callable, Dict, Optional, Union, cast
from unittest import mock

from discord import Guild, Member, Role, TextChannel, User
import pytest
from pytest import MonkeyPatch

from .birthday import Birthday
from .constants import (
    BASE_GUILD_MEMBER,
    BOT_BIRTHDAY_MSG,
    CANNED_MESSAGES,
    DEFAULT_YEAR,
    KEY_BDAY_CHANNEL,
    KEY_BDAY_DAY,
    KEY_BDAY_MONTH,
    KEY_BDAY_ROLE,
    KEY_IS_ASSIGNED,
)


class TestGetBirthdayMessage:
    @dataclasses.dataclass
    class MemberInfo:
        memberId: int
        mention: str

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "memberInfo",
        (
            MemberInfo(memberId=1111, mention="Onii-chan"),
            MemberInfo(memberId=2222, mention="Ara-ara Onee-chan"),
            MemberInfo(memberId=3333, mention="SENPAI"),
            MemberInfo(memberId=4444, mention="Sensei"),
        ),
    )
    async def testNormalUser(
        self,
        cogBirthday: Birthday,
        mockUserWith: Callable[..., Union[mock.Mock, User]],
        memberInfo: MemberInfo,
    ):
        mockUser = mockUserWith(id=memberInfo.memberId, mention=memberInfo.mention)
        expectedMessages = [msg.format(mockUser.mention) for msg in CANNED_MESSAGES]

        msg = cogBirthday.getBirthdayMessage(user=mockUser)
        assert msg in expectedMessages

    @pytest.mark.asyncio
    async def testBotUser(self, cogBirthday: Birthday):
        assert cogBirthday.bot.user is not None
        msg = cogBirthday.getBirthdayMessage(user=cogBirthday.bot.user)
        assert msg == BOT_BIRTHDAY_MSG


@pytest.mark.asyncio
async def testDailySweep(
    monkeypatch: MonkeyPatch,
    cogBirthday: Birthday,
    mockGuild: Union[mock.Mock, Guild],
    mockRole: Union[mock.Mock, Role],
    mockMemberWith: Callable[..., Union[mock.Mock, Member]],
):
    # prep role
    bdayRoleConfig = cogBirthday.config.guild(guild=mockGuild).get_attr(KEY_BDAY_ROLE)
    await bdayRoleConfig.set(value=mockRole.id)

    # prep members
    memberNames = {"ayaka", "barbara", "childe", "dainsleif"}
    memberMap: Dict[str, Union[mock.Mock, Member]] = {
        name: mockMemberWith(id=i, name=name, remove_roles=mock.AsyncMock())
        for i, name in enumerate(memberNames)
    }
    memberConfigMap: Dict[str, Dict[str, Any]] = {
        "ayaka": {
            KEY_BDAY_MONTH: 9,
            KEY_BDAY_DAY: 28,
            KEY_IS_ASSIGNED: False,
        },
        "barbara": {
            KEY_BDAY_MONTH: 7,
            KEY_BDAY_DAY: 5,
            KEY_IS_ASSIGNED: True,
        },
        "childe": {
            KEY_BDAY_MONTH: 7,
            KEY_BDAY_DAY: 20,
            KEY_IS_ASSIGNED: True,
        },
        "dainsleif": {
            # no birthday set
            KEY_IS_ASSIGNED: False,
        },
    }

    # finalize the config map with the base config applied for members
    fullMemberConfigMap: Dict[str, Dict[str, Any]] = {}
    for memberName, expectedMemberConfig in memberConfigMap.items():
        fullMemberConfig = BASE_GUILD_MEMBER.copy()
        fullMemberConfig.update(expectedMemberConfig)
        fullMemberConfigMap[memberName] = fullMemberConfig

    for memberName, expectedMemberConfig in fullMemberConfigMap.items():
        for configKey, configValue in expectedMemberConfig.items():
            memberConfig = cogBirthday.config.member(member=memberMap[memberName])
            await memberConfig.get_attr(configKey).set(configValue)

    # assume this date and time is when the `_dailySweep` function gets called
    testDateTime = datetime(
        year=DEFAULT_YEAR,
        month=memberConfigMap["barbara"][KEY_BDAY_MONTH],
        day=memberConfigMap["barbara"][KEY_BDAY_DAY],
    )

    # Only Childe is affected, i.e., their birthday role gets removed
    # because:
    # - Ayaka does not have the birthday role despite having the birthday set.
    # - Barbara's birthday is the same as the `testDateTime`.
    # - Dainsleif has no birthday set.
    expectedAffectedMemberNames = {"childe"}

    expectedMemberConfigMap: Dict[str, Dict[str, Any]] = {
        memberName: memberConfig.copy() for memberName, memberConfig in fullMemberConfigMap.items()
    }

    for memberName in expectedAffectedMemberNames:
        expectedMemberConfigMap[memberName][KEY_IS_ASSIGNED] = False

    # mock/patch
    def mockTimeStrftime(format, t: Any = None) -> str:
        """A mock function to be patched for `time.strftime`."""

        # This function should not make any `strftime` method call via a `time` object
        # because it will result in a recursion error after monkey-patching `time.strftime`.

        return {
            "%d": str(testDateTime.day),
        }[format]

    async def mockAllMembers(guild: Guild) -> Dict[int, Dict[str, Any]]:
        """A mock function to be patched for `redbot.core.Config.all_members`."""
        assert guild.id == mockGuild.id
        return {
            memberMap[memberName].id: memberConfig
            for memberName, memberConfig in memberConfigMap.items()
        }

    with monkeypatch.context() as patchContext:
        patchContext.setattr(
            target=cogBirthday.bot,
            name="guilds",
            value=[mockGuild],
        )
        patchContext.setattr(
            target=cogBirthday.config,
            name="all_members",
            value=mockAllMembers,
        )
        patchContext.setattr(
            target=mockGuild,
            name="roles",
            value=[mockRole],
        )
        patchContext.setattr(
            target=mockGuild,
            name="members",
            value=tuple(memberMap.values()),
        )
        patchContext.setattr(
            target=time,
            name="localtime",
            value=mock.Mock(return_value=testDateTime.timetuple()),
        )
        patchContext.setattr(
            target=time,
            name="strftime",
            value=mockTimeStrftime,
        )

        await cogBirthday._dailySweep()

    for memberName, expectedMemberConfig in expectedMemberConfigMap.items():
        actualMemberConfig = await cogBirthday.config.member(member=memberMap[memberName]).all()
        assert actualMemberConfig == expectedMemberConfig

    for memberName in memberNames:
        mockedRemoveRolesMethod = cast(mock.AsyncMock, memberMap[memberName].remove_roles)

        if memberName in expectedAffectedMemberNames:
            assert mockedRemoveRolesMethod.await_count
            assert mockedRemoveRolesMethod.await_args

            role: Optional[Role]
            roleCheck: bool = False
            for role in mockedRemoveRolesMethod.await_args.args:
                if role is not None and role.id == mockRole.id:
                    roleCheck = True
                    break

            assert roleCheck

        else:
            assert not mockedRemoveRolesMethod.await_count


@pytest.mark.asyncio
async def testDailyAdd(
    monkeypatch: MonkeyPatch,
    cogBirthday: Birthday,
    mockGuild: Union[mock.Mock, Guild],
    mockRole: Union[mock.Mock, Role],
    mockTextChannel: Union[mock.Mock, TextChannel],
    mockMemberWith: Callable[..., Union[mock.Mock, Member]],
):
    # prep role
    bdayRoleConfig = cogBirthday.config.guild(guild=mockGuild).get_attr(KEY_BDAY_ROLE)
    await bdayRoleConfig.set(value=mockRole.id)

    # prep channel
    bdayChannelConfig = cogBirthday.config.guild(guild=mockGuild).get_attr(KEY_BDAY_CHANNEL)
    await bdayChannelConfig.set(mockTextChannel.id)

    # prep members
    memberNames = {"arisu", "momoka", "miria", "risa"}
    memberMap: Dict[str, Union[mock.Mock, Member]] = {
        name: mockMemberWith(id=i, name=name, add_roles=mock.AsyncMock())
        for i, name in enumerate(memberNames)
    }
    memberConfigMap: Dict[str, Dict[str, Any]] = {
        "arisu": {
            KEY_BDAY_MONTH: 7,
            KEY_BDAY_DAY: 31,
            KEY_IS_ASSIGNED: False,
        },
        "momoka": {
            KEY_BDAY_MONTH: 4,
            KEY_BDAY_DAY: 8,
            KEY_IS_ASSIGNED: False,
        },
        "miria": {
            KEY_BDAY_MONTH: 4,
            KEY_BDAY_DAY: 14,
            KEY_IS_ASSIGNED: False,
        },
        "risa": {
            KEY_BDAY_MONTH: 11,
            KEY_BDAY_DAY: 19,
            KEY_IS_ASSIGNED: False,
        },
    }

    # finalize the config map with the base config applied for members
    fullMemberConfigMap: Dict[str, Dict[str, Any]] = {}
    for memberName, expectedMemberConfig in memberConfigMap.items():
        fullMemberConfig = BASE_GUILD_MEMBER.copy()
        fullMemberConfig.update(expectedMemberConfig)
        fullMemberConfigMap[memberName] = fullMemberConfig

    for memberName, expectedMemberConfig in fullMemberConfigMap.items():
        for configKey, configValue in expectedMemberConfig.items():
            memberConfig = cogBirthday.config.member(member=memberMap[memberName])
            await memberConfig.get_attr(configKey).set(configValue)

    # assume this date and time is when the `_dailyAdd` function gets called
    testDateTime = datetime(
        year=DEFAULT_YEAR,
        month=memberConfigMap["momoka"][KEY_BDAY_MONTH],
        day=memberConfigMap["momoka"][KEY_BDAY_DAY],
    )

    # Only Momoka is affected, i.e., the birthday role is added.
    expectedAffectedMemberNames = {"momoka"}

    expectedMemberConfigMap: Dict[str, Dict[str, Any]] = {
        memberName: memberConfig.copy() for memberName, memberConfig in fullMemberConfigMap.items()
    }

    for memberName in expectedAffectedMemberNames:
        expectedMemberConfigMap[memberName][KEY_IS_ASSIGNED] = True

    # mock/patch
    def mockTimeStrftime(format, t: Any = None) -> str:
        """A mock function to be patched for `time.strftime`."""
        # This function should not make any `strftime` method call via a `time` object
        # because it will result in a recursion error after monkey-patching `time.strftime`.

        return {
            "%d": str(testDateTime.day),
            "%m": str(testDateTime.month),
        }[format]

    async def mockAllMembers(guild: Guild) -> Dict[int, Dict[str, Any]]:
        """A mock function to be patched for `redbot.core.Config.all_members`."""
        assert guild.id == mockGuild.id
        return {
            memberMap[memberName].id: memberConfig
            for memberName, memberConfig in memberConfigMap.items()
        }

    with monkeypatch.context() as patchContext:
        patchContext.setattr(
            target=cogBirthday.bot,
            name="guilds",
            value=[mockGuild],
        )
        patchContext.setattr(
            target=cogBirthday.config,
            name="all_members",
            value=mockAllMembers,
        )
        patchContext.setattr(
            target=mockGuild,
            name="roles",
            value=[mockRole],
        )
        patchContext.setattr(
            target=mockGuild,
            name="members",
            value=tuple(memberMap.values()),
        )
        patchContext.setattr(
            target=mockGuild,
            name="channels",
            value=[mockTextChannel],
        )
        patchContext.setattr(
            target=time,
            name="localtime",
            value=mock.Mock(return_value=testDateTime.timetuple()),
        )
        patchContext.setattr(
            target=time,
            name="strftime",
            value=mockTimeStrftime,
        )

        await cogBirthday._dailyAdd()

    for memberName, expectedMemberConfig in expectedMemberConfigMap.items():
        actualMemberConfig = await cogBirthday.config.member(member=memberMap[memberName]).all()
        assert actualMemberConfig == expectedMemberConfig

    for memberName in memberNames:
        mockedAddRolesMethod = cast(mock.AsyncMock, memberMap[memberName].add_roles)

        if memberName in expectedAffectedMemberNames:
            assert mockedAddRolesMethod.await_count
            assert mockedAddRolesMethod.await_args

            role: Optional[Role]
            roleCheck: bool = False
            for role in mockedAddRolesMethod.await_args.args:
                if role is not None and role.id == mockRole.id:
                    roleCheck = True
                    break

            assert roleCheck

        else:
            assert not mockedAddRolesMethod.await_count
