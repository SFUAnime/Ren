import asyncio
import dataclasses
import datetime
from typing import Awaitable, Callable, List, Optional, Tuple, Union, cast
from unittest import mock

from discord import DMChannel, Embed, Forbidden, Guild, Member, Message, Role, TextChannel
from discord.abc import Snowflake
from discord.utils import SnowflakeList
import pytest
from pytest import MonkeyPatch

from redbot.core.commands.context import Context

from . import commandsCore
from .birthday import Birthday
from .constants import (
    DEFAULT_YEAR,
    KEY_ADDED_BEFORE,
    KEY_ALLOW_SELF_BDAY,
    KEY_BDAY_CHANNEL,
    KEY_BDAY_DAY,
    KEY_BDAY_MONTH,
    KEY_BDAY_ROLE,
    KEY_IS_ASSIGNED,
)


def birthdayOn(month: int, day: int) -> datetime.date:
    return datetime.date(year=DEFAULT_YEAR, month=month, day=day)


def contentFromMockMessageableSend(
    sendFn: Union[mock.AsyncMock, Callable[..., Awaitable[Message]]],
):
    """The value of the `content` argument of `ctxSend`.
    The provided `ctxSend` should be a mock object resembling
    `discord.abc.Messageable.send`.
    """

    assert isinstance(sendFn, mock.AsyncMock)
    assert sendFn.await_count
    assert sendFn.await_args

    invokeArgs = sendFn.await_args
    return invokeArgs.kwargs.get("content") or invokeArgs.args[0]


class TestCmdSetChannel:
    @pytest.mark.asyncio
    async def test(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockTextChannel: Union[mock.Mock, TextChannel],
    ):
        # prep
        mockContext.guild = mockGuild
        expectedChannel = mockTextChannel
        expectedChannel.name = "TestChannel"

        # test
        await cogBirthday.cmdSetChannel(ctx=mockContext, channel=expectedChannel)

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        channelIdConfig = guildConfig.get_attr(item=KEY_BDAY_CHANNEL)
        actualChannelId: Optional[int] = await channelIdConfig()
        assert actualChannelId == expectedChannel.id

        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert expectedChannel.name in actualReply
        assert "has been set as the birthday mention channel" in actualReply

    @pytest.mark.asyncio
    async def testNone(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
    ):
        """Test to ensure the command works as expected when the role is set to `None`."""

        # prep
        mockContext.guild = mockGuild

        # test
        await cogBirthday.cmdSetChannel(ctx=mockContext, channel=None)

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        channelIdConfig = guildConfig.get_attr(item=KEY_BDAY_CHANNEL)
        actualChannelId: Optional[int] = await channelIdConfig()
        assert actualChannelId is None

        expectedReply = "Birthday mentions are now disabled"
        assert expectedReply in contentFromMockMessageableSend(sendFn=mockContext.send)


class TestCmdSetRole:
    @pytest.mark.asyncio
    async def test(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockRole: Union[mock.Mock, Role],
    ):
        # prep
        mockContext.guild = mockGuild
        expectedRole = mockRole
        expectedRole.name = "TestRole"

        # test
        await cogBirthday.cmdSetRole(ctx=mockContext, role=expectedRole)

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleIdConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)
        actualRoleId: Optional[int] = await roleIdConfig()
        assert actualRoleId == expectedRole.id

        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert expectedRole.name in actualReply
        assert "has been set as the birthday role" in actualReply


class TestCmdAddMemberBirthday:
    memberName: str = "TestMember"

    @dataclasses.dataclass
    class Case:
        birthday: datetime.date = dataclasses.field(
            default_factory=lambda: birthdayOn(month=2, day=29)
        )
        birthdayStr: str = "February 29"
        addedBefore: bool = False
        previousMonth: Optional[int] = None
        previousDay: Optional[int] = None
        promptAnswerForReAddIfPreviouslyRemoved: Optional[str] = None
        expectedMonth: Optional[int] = 2
        expectedDay: Optional[int] = 29
        expectedReply: str = "expected reply"
        expectedCheckBirthdayInvoked: bool = False

    cases = (
        Case(
            # no previous birthday
            addedBefore=False,
            previousMonth=None,
            previousDay=None,
            expectedReply=f"added",
            expectedCheckBirthdayInvoked=True,
        ),
        Case(
            # previous birthday exists
            addedBefore=True,
            previousMonth=2,
            previousDay=8,
            expectedReply=f"updated",
            expectedCheckBirthdayInvoked=True,
        ),
        Case(
            # birthday was added and removed at one point
            addedBefore=True,
            previousMonth=None,
            previousDay=None,
            promptAnswerForReAddIfPreviouslyRemoved="yes",
            expectedReply=f"added",
            expectedCheckBirthdayInvoked=True,
        ),
        Case(
            # the user does not decide whether to re-add a deleted birthday
            addedBefore=True,
            previousMonth=None,
            previousDay=None,
            promptAnswerForReAddIfPreviouslyRemoved=None,
            expectedMonth=None,
            expectedDay=None,
            expectedReply="took too long, not re-adding",
            expectedCheckBirthdayInvoked=False,
        ),
        Case(
            # the user decides to not re-add a deleted birthday
            addedBefore=True,
            previousMonth=None,
            previousDay=None,
            promptAnswerForReAddIfPreviouslyRemoved="no",
            expectedMonth=None,
            expectedDay=None,
            expectedReply="Not re-adding",
            expectedCheckBirthdayInvoked=False,
        ),
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", cases)
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
        mockRole: Union[mock.Mock, Role],
        case: Case,
    ):
        # prep context and member
        mockContext.guild = mockGuild
        mockMember.name = self.memberName

        # prep config
        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)

        memberConfig = cogBirthday.config.member(member=mockMember)
        addedBeforeConfig = memberConfig.get_attr(item=KEY_ADDED_BEFORE)
        birthMonthConfig = memberConfig.get_attr(item=KEY_BDAY_MONTH)
        birthDayConfig = memberConfig.get_attr(item=KEY_BDAY_DAY)

        await roleConfig.set(value=mockRole.id)
        await addedBeforeConfig.set(value=case.addedBefore)
        await birthMonthConfig.set(value=case.previousMonth)
        await birthDayConfig.set(value=case.previousDay)

        # mock out checkBirthday - it should be separately tested
        mockCheckBirthday = mock.AsyncMock()

        # prep for user prompt about re-adding birthday
        # for a member whose birthday was previously deleted
        if case.promptAnswerForReAddIfPreviouslyRemoved is None:
            promptExceptionForReAddIfPreviouslyRemoved = asyncio.TimeoutError()
            promptReturnForReAddIfPreviouslyRemoved = None
        else:
            promptExceptionForReAddIfPreviouslyRemoved = None
            promptReturnForReAddIfPreviouslyRemoved = mock.create_autospec(
                spec=Message,
                content=case.promptAnswerForReAddIfPreviouslyRemoved,
            )

        # mock/patch the bot's wait_for
        with monkeypatch.context() as patchContext:
            patchContext.setattr(
                target=cogBirthday.bot,
                name="wait_for",
                value=mock.AsyncMock(
                    side_effect=promptExceptionForReAddIfPreviouslyRemoved,
                    return_value=promptReturnForReAddIfPreviouslyRemoved,
                ),
            )
            patchContext.setattr(target=cogBirthday, name="checkBirthday", value=mockCheckBirthday)
            patchContext.setattr(target=asyncio, name="sleep", value=mock.AsyncMock())

            # run the command
            await cogBirthday.cmdAddMemberBirthday(
                ctx=mockContext,
                member=mockMember,
                birthday=case.birthday,
            )

        # confirm config values
        actualAddedBefore: bool = await addedBeforeConfig()
        actualBirthdayMonth: Optional[int] = await birthMonthConfig()
        actualBirthdayDay: Optional[int] = await birthDayConfig()

        assert actualAddedBefore == True
        assert actualBirthdayMonth == case.expectedMonth
        assert actualBirthdayDay == case.expectedDay

        # confirm reply
        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert case.expectedReply in actualReply
        if "added" in case.expectedReply or "updated" in case.expectedReply:
            assert self.memberName in actualReply
            assert case.birthdayStr in actualReply

        # confirm whether checkBirthday has been invoked
        # so that there is celebration for the member
        # in case their birthday be the same as the added month and day
        if case.expectedCheckBirthdayInvoked:
            assert mockCheckBirthday.await_count != 0

    @pytest.mark.asyncio
    async def testNoRole(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
    ):
        """Test to ensure the command complains as expected when the birthday role is `None`."""

        mockContext.guild = mockGuild

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleIdConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)
        await roleIdConfig.set(value=None)

        with monkeypatch.context() as patchContext:
            patchContext.setattr(
                target=cogBirthday.bot,
                name="wait_for",
                value=mock.AsyncMock(),
            )
            patchContext.setattr(target=cogBirthday, name="checkBirthday", value=mock.AsyncMock())
            patchContext.setattr(target=asyncio, name="sleep", value=mock.AsyncMock())
            await cogBirthday.cmdAddMemberBirthday(
                ctx=mockContext,
                member=mockMember,
                birthday=birthdayOn(month=8, day=31),
            )

        assert "please set a role" in contentFromMockMessageableSend(sendFn=mockContext.send)


class TestCmdListBirthdays:
    @pytest.mark.asyncio
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMemberWith: Callable[..., Member],
    ):
        # prep context
        mockContext.guild = mockGuild

        # prep birthdays and members
        birthdayToMembersMap = {
            birthdayOn(month=2, day=29): [mockMemberWith(id=3, name="Alice")],
            birthdayOn(month=4, day=30): [mockMemberWith(id=9, name="Bob")],
            birthdayOn(month=8, day=31): [mockMemberWith(id=39, name="ミク")],
        }
        birthdayStrMap = {
            birthdayOn(month=2, day=29).toordinal(): "February 29",
            birthdayOn(month=4, day=30).toordinal(): "April 30",
            birthdayOn(month=8, day=31).toordinal(): "August 31",
        }

        expectedReplyEmbedDescription = "\n".join(
            f"{birthdayStrMap[birthday.toordinal()]}: {member.name}"
            for birthday, members in birthdayToMembersMap.items()
            for member in members
        )

        for birthday, members in birthdayToMembersMap.items():
            for member in members:
                memberConfig = cogBirthday.config.member(member=member)
                await memberConfig.get_attr(item=KEY_BDAY_MONTH).set(value=birthday.month)
                await memberConfig.get_attr(item=KEY_BDAY_DAY).set(value=birthday.day)
                await memberConfig.get_attr(item=KEY_ADDED_BEFORE).set(value=True)

        # mock/patch the function for constructing a menu
        mockMenu = mock.AsyncMock()
        monkeypatch.setattr(target=commandsCore, name="menu", value=mockMenu)

        # assume the list of members for the current guild
        memberSet = {
            member.id: member for members in birthdayToMembersMap.values() for member in members
        }
        memberList = list(memberSet.values())
        monkeypatch.setattr(target=mockContext.guild, name="members", value=memberList)

        # run the command
        await cogBirthday.cmdListBirthdays(ctx=mockContext)

        # confirm the embeds' contents are as expected
        assert mockMenu.await_count
        assert mockMenu.await_args
        mockMenuInvokeArgs = mockMenu.await_args
        pages: Union[List[str], List[Embed]] = (
            mockMenuInvokeArgs.kwargs.get("pages") or mockMenuInvokeArgs.args[1]
        )

        actualReplyEmbedDescriptions = []

        for page in pages:
            assert isinstance(page, Embed)
            actualReplyEmbedDescriptions.append(page.description)

        assert "\n".join(actualReplyEmbedDescriptions) == expectedReplyEmbedDescription

    @pytest.mark.asyncio
    async def testEmpty(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
    ):
        """Test to ensure the command complains as expected when there are no birthdays."""

        mockContext.guild = mockGuild
        await cogBirthday.cmdListBirthdays(ctx=mockContext)

        expectedReply = "There are no birthdates set on this server"
        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert expectedReply in actualReply


class TestCmdUnassignRole:
    @pytest.mark.asyncio
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
        mockRole: Union[mock.Mock, Role],
    ):
        # prep
        birthdayRole = mockRole

        monkeypatch.setattr(target=mockGuild, name="roles", value=[birthdayRole])
        mockContext.guild = mockGuild

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleConfig = guildConfig.get_attr(KEY_BDAY_ROLE)
        await roleConfig.set(value=birthdayRole.id)

        mockMember.name = "TestMember"
        monkeypatch.setattr(
            target=mockMember,
            name="roles",
            value=SnowflakeList(data=[birthdayRole.id]),
        )

        # mock/patch
        mockRemoveRoles = mock.AsyncMock()
        mockMember.remove_roles = mockRemoveRoles

        # test
        await cogBirthday.cmdUnassignRole(ctx=mockContext, member=mockMember)

        assert mockRemoveRoles.await_count
        assert mockRemoveRoles.await_args

        removedRoles = cast(Tuple[Snowflake], mockRemoveRoles.await_args.args)
        assert birthdayRole.id in (role.id for role in removedRoles)

        memberConfig = cogBirthday.config.member(member=mockMember)
        isAssignedConfig = memberConfig.get_attr(KEY_IS_ASSIGNED)

        actualIsAssigned: bool = await isAssignedConfig()
        assert actualIsAssigned == False

        expectedReply = f"Successfully unassigned **{mockMember.name}** from the birthday role"
        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert expectedReply in actualReply

    @pytest.mark.asyncio
    async def testNoRole(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
    ):
        """Test to ensure the command complains as expected when the birthday role is `None`."""

        mockContext.guild = mockGuild

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleIdConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)
        await roleIdConfig.set(value=None)

        await cogBirthday.cmdUnassignRole(ctx=mockContext, member=mockMember)
        assert "please set a role" in contentFromMockMessageableSend(sendFn=mockContext.send)


class TestCmdDeleteMemberBirthday:
    cases = (
        birthdayOn(month=3, day=9),  # birthday set
        None,  # birthday not set yet
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", cases)
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
        mockRole: Union[mock.Mock, Role],
        case: Optional[datetime.date],
    ):
        # prep
        birthdayRole = mockRole
        mockContext.guild = mockGuild

        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        roleConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)
        await roleConfig.set(value=mockRole.id)

        monkeypatch.setattr(target=mockContext.guild, name="roles", value=[birthdayRole])
        monkeypatch.setattr(target=mockMember, name="roles", value=[birthdayRole.id])

        if case:
            memberConfig = cogBirthday.config.member(member=mockMember)
            birthMonthConfig = memberConfig.get_attr(item=KEY_BDAY_MONTH)
            birthDayConfig = memberConfig.get_attr(item=KEY_BDAY_DAY)

            await birthMonthConfig.set(value=case.month)
            await birthDayConfig.set(value=case.day)

        # mock/patch
        mockMember.remove_roles = mock.AsyncMock()

        # test
        await cogBirthday.cmdDeleteMemberBirthday(ctx=mockContext, member=mockMember)

        assert mockMember.remove_roles.await_count
        assert mockMember.remove_roles.await_args
        removedRoles = cast(Tuple[Snowflake], mockMember.remove_roles.await_args.args)
        assert birthdayRole.id in (role.id for role in removedRoles)

        memberConfig = cogBirthday.config.member(member=mockMember)
        addedBeforeConfig = memberConfig.get_attr(item=KEY_ADDED_BEFORE)
        birthMonthConfig = memberConfig.get_attr(item=KEY_BDAY_MONTH)
        birthDayConfig = memberConfig.get_attr(item=KEY_BDAY_DAY)
        isAssignedConfig = memberConfig.get_attr(KEY_IS_ASSIGNED)

        actualAddedBefore: bool = await addedBeforeConfig()
        actualBirthdayMonth: Optional[int] = await birthMonthConfig()
        actualBirthdayDay: Optional[int] = await birthDayConfig()
        actualIsAssigned: bool = await isAssignedConfig()

        assert actualAddedBefore == True
        assert actualBirthdayMonth == None
        assert actualBirthdayDay == None
        assert actualIsAssigned == False

        expectedReply = f"Deleted birthday of **{mockMember.name}**"
        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert expectedReply in actualReply


class TestCmdGetSelfBirthday:
    birthday = birthdayOn(month=3, day=9)
    birthdayStr = "March 09"

    @dataclasses.dataclass
    class Case:
        dmBlocked: bool = False
        promptAnswerForContinueWithoutDm: Optional[str] = None
        expectedReplyToAuthor: Optional[str] = None
        expectedReplyToContext: Optional[str] = None

    cases = (
        Case(
            # has birthday
            expectedReplyToAuthor=f"Your birthday is ||**{birthdayStr}**||",
        ),
        Case(
            # DMs blocked, user does not answer whether to continue without DMs
            dmBlocked=True,
            promptAnswerForContinueWithoutDm=None,
            expectedReplyToContext="Aborting",
        ),
        Case(
            # DMs blocked, user wants to continue without DMs
            dmBlocked=True,
            promptAnswerForContinueWithoutDm="yes",
            expectedReplyToContext=f"Your birthday is ||**{birthdayStr}**||",
        ),
        Case(
            # DMs blocked, user does not want to continue without DMs
            dmBlocked=True,
            promptAnswerForContinueWithoutDm="no",
            expectedReplyToContext="Aborting",
        ),
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", cases)
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
        case: Case,
    ) -> None:
        # prep member
        mockMemberSend = mock.AsyncMock()
        if case.dmBlocked:
            mockMemberSend.side_effect = Forbidden(response=mock.Mock(), message=None)
        mockMember.send = mockMemberSend

        # prep config
        memberConfig = cogBirthday.config.member(member=mockMember)
        birthMonthConfig = memberConfig.get_attr(item=KEY_BDAY_MONTH)
        birthDayConfig = memberConfig.get_attr(item=KEY_BDAY_DAY)

        await birthMonthConfig.set(value=self.birthday.month)
        await birthDayConfig.set(value=self.birthday.day)

        # prep context
        mockContext.author = mockMember
        mockContext.guild = mockGuild

        # prep for user prompt about re-adding birthday
        # for a member whose birthday was previously deleted
        if case.promptAnswerForContinueWithoutDm is None:
            promptExceptionForContinueWithoutDm = asyncio.TimeoutError()
            promptReturnForContinueWithoutDm = None
        else:
            promptExceptionForContinueWithoutDm = None
            promptReturnForContinueWithoutDm = mock.create_autospec(
                spec=Message,
                content=case.promptAnswerForContinueWithoutDm,
            )

        # test
        with monkeypatch.context() as patchContext:
            patchContext.setattr(
                target=cogBirthday.bot,
                name="wait_for",
                value=mock.AsyncMock(
                    side_effect=promptExceptionForContinueWithoutDm,
                    return_value=promptReturnForContinueWithoutDm,
                ),
            )

            await cogBirthday.cmdGetSelfBirthday(
                ctx=mockContext,
                cmdSetSelfBirthday=cogBirthday._cmdSetSelfBirthday,
            )

        if case.expectedReplyToAuthor is not None:
            actualReply = contentFromMockMessageableSend(sendFn=mockContext.author.send)
            assert case.expectedReplyToAuthor in actualReply

        if case.expectedReplyToContext is not None:
            actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
            assert case.expectedReplyToContext in actualReply

    @pytest.mark.asyncio
    async def testNoBirthday(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
    ):
        await cogBirthday.cmdGetSelfBirthday(
            ctx=mockContext,
            cmdSetSelfBirthday=cogBirthday._cmdSetSelfBirthday,
        )

        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert "Your birthday in this server has not been set" in actualReply


class TestCmdSetSelfBirthday:
    birthday = birthdayOn(month=2, day=29)
    birthdayStr = "February 29"

    @dataclasses.dataclass
    class Case:
        selfBirthdayEnabled: bool = False
        previousBirthMonth: Optional[int] = None
        previousBirthDay: Optional[int] = None
        birthdayRoleConfigured: bool = False
        dmBlocked: bool = False
        promptAnswerForContinueWithoutDm: Optional[str] = None
        promptAnswerForBirthdayConfirmation: Optional[str] = None
        expectedBirthMonth: Optional[int] = None
        expectedBirthDay: Optional[int] = None
        expectedReplyToAuthor: Optional[str] = None
        expectedReplyToContext: Optional[str] = None
        expectedCheckBirthdayInvoked: bool = False

    cases = (
        Case(
            # self-birthday functionality is not enabled
            selfBirthdayEnabled=False,
            expectedReplyToContext="This function is not enabled",
        ),
        Case(
            # birthday has already been set
            selfBirthdayEnabled=True,
            previousBirthMonth=3,
            previousBirthDay=9,
            expectedReplyToContext="Your birthday is already set",
            expectedBirthMonth=3,  # unchanged compared to the already-set birth month
            expectedBirthDay=9,  # unchanged compared to the already-set birth day
        ),
        Case(
            # birthday role is not configured
            selfBirthdayEnabled=True,
            birthdayRoleConfigured=False,
            expectedReplyToContext="This server is not configured",
        ),
        Case(
            # DMs OK
            selfBirthdayEnabled=True,
            birthdayRoleConfigured=True,
            dmBlocked=False,
            promptAnswerForBirthdayConfirmation="yes",
            expectedBirthMonth=birthday.month,
            expectedBirthDay=birthday.day,
            expectedReplyToAuthor=f"Successfully set your birthday to ||**{birthdayStr}**||",
            expectedCheckBirthdayInvoked=True,
        ),
        Case(
            # DMs blocked
            selfBirthdayEnabled=True,
            birthdayRoleConfigured=True,
            dmBlocked=True,
            promptAnswerForContinueWithoutDm="yes",
            promptAnswerForBirthdayConfirmation="yes",
            expectedBirthMonth=birthday.month,
            expectedBirthDay=birthday.day,
            expectedReplyToContext=f"Successfully set your birthday to ||**{birthdayStr}**||",
            expectedCheckBirthdayInvoked=True,
        ),
        Case(
            # DMs OK, but birthday confirmation is not "yes"
            selfBirthdayEnabled=True,
            birthdayRoleConfigured=True,
            dmBlocked=False,
            promptAnswerForBirthdayConfirmation="no",
            expectedReplyToAuthor="Not setting your birthday",
        ),
        Case(
            # DMs blocked, and either:
            # - confirmation for continuing without DMs is not "yes", or
            # - birthday confirmation is not "yes"
            selfBirthdayEnabled=True,
            birthdayRoleConfigured=True,
            dmBlocked=True,
            promptAnswerForContinueWithoutDm="no",
            promptAnswerForBirthdayConfirmation="no",
            expectedReplyToContext="Not setting your birthday",
        ),
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", cases)
    async def test(
        self,
        monkeypatch: MonkeyPatch,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        mockMember: Union[mock.Mock, Member],
        mockRole: Union[mock.Mock, Role],
        mockTextChannel: Union[mock.Mock, TextChannel],
        case: Case,
    ) -> None:
        # prep guild
        mockContext.guild = mockGuild
        mockContext.channel = mockTextChannel
        mockContext.channel.send = mock.AsyncMock()

        # prep member
        mockMember.send = mock.AsyncMock()
        mockContext.author = mockMember

        # prep config
        guildConfig = cogBirthday.config.guild(guild=mockContext.guild)
        memberConfig = cogBirthday.config.member(member=mockContext.author)

        allowSelfBdayConfig = guildConfig.get_attr(item=KEY_ALLOW_SELF_BDAY)
        bdayRoleConfig = guildConfig.get_attr(item=KEY_BDAY_ROLE)
        birthMonthConfig = memberConfig.get_attr(item=KEY_BDAY_MONTH)
        birthDayConfig = memberConfig.get_attr(item=KEY_BDAY_DAY)

        await allowSelfBdayConfig.set(value=case.selfBirthdayEnabled)
        await bdayRoleConfig.set(value=mockRole.id if case.birthdayRoleConfigured else None)
        await birthMonthConfig.set(value=case.previousBirthMonth)
        await birthDayConfig.set(value=case.previousBirthDay)

        # mock/patch context author's send
        if case.dmBlocked:
            mockMember.send.side_effect = Forbidden(response=mock.Mock(), message=None)

        # mock/patch checkBirthday
        mockCheckBirthday = mock.AsyncMock()

        # mock/patch the bot's wait_for
        waitForSideEffects = []

        if case.dmBlocked:
            waitForSideEffects.append(
                asyncio.TimeoutError()
                if case.promptAnswerForContinueWithoutDm is None
                else mock.create_autospec(
                    spec=Message,
                    author=mockContext.author,
                    channel=mockContext.channel,
                    content=case.promptAnswerForContinueWithoutDm,
                )
            )

        waitForSideEffects.append(
            asyncio.TimeoutError()
            if case.promptAnswerForBirthdayConfirmation is None
            else mock.create_autospec(
                spec=Message,
                author=mockContext.author,
                channel=mockContext.author.dm_channel,
                content=case.promptAnswerForBirthdayConfirmation,
            )
        )

        with monkeypatch.context() as patchContext:
            patchContext.setattr(
                target=cogBirthday.bot,
                name="wait_for",
                value=mock.AsyncMock(side_effect=waitForSideEffects),
            )
            patchContext.setattr(target=cogBirthday, name="checkBirthday", value=mockCheckBirthday)

            # run the command
            await cogBirthday.cmdSetSelfBirthday(ctx=mockContext, birthday=self.birthday)

        # confirm config values
        actualBirthdayMonth: Optional[int] = await birthMonthConfig()
        actualBirthdayDay: Optional[int] = await birthDayConfig()

        assert actualBirthdayMonth == case.expectedBirthMonth
        assert actualBirthdayDay == case.expectedBirthDay

        # confirm reply
        if case.expectedReplyToAuthor is not None:
            assert case.expectedReplyToAuthor in contentFromMockMessageableSend(
                sendFn=mockMember.send
            )

        if case.expectedReplyToContext is not None:
            assert case.expectedReplyToContext in contentFromMockMessageableSend(
                sendFn=mockContext.send
            ) or case.expectedReplyToContext in contentFromMockMessageableSend(
                sendFn=mockContext.channel.send
            )

        # confirm whether checkBirthday has been invoked
        # so that there is celebration for the member
        # in case their birthday be the same as the added month and day
        if case.expectedCheckBirthdayInvoked:
            assert mockCheckBirthday.await_count


class TestCmdToggleSelfBirthday:
    @dataclasses.dataclass
    class Case:
        initialValue: bool
        expectedReply: str = "expected reply"

        def expectedValue(self) -> bool:
            return not self.initialValue

    cases = (
        Case(initialValue=False, expectedReply="Enabled"),
        Case(initialValue=True, expectedReply="Disabled"),
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", cases)
    async def test(
        self,
        cogBirthday: Birthday,
        mockContext: Union[mock.Mock, Context],
        mockGuild: Union[mock.Mock, Guild],
        case: Case,
    ):
        mockContext.guild = mockGuild

        guildConfig = cogBirthday.config.guild(mockGuild)
        allowSelfBirthdayConfig = guildConfig.get_attr(KEY_ALLOW_SELF_BDAY)
        await allowSelfBirthdayConfig.set(case.initialValue)

        await cogBirthday.cmdToggleSelfBirthday(ctx=mockContext)

        actualAllowSelfBirthday: bool = await allowSelfBirthdayConfig()
        assert actualAllowSelfBirthday == case.expectedValue()

        actualReply = contentFromMockMessageableSend(sendFn=mockContext.send)
        assert case.expectedReply in actualReply
