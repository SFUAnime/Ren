from asyncio import AbstractEventLoop
import locale
from typing import AsyncGenerator, Callable, Generator, Optional, Sequence, Union
from unittest import mock

from discord import ClientUser, Guild, Member, Role, TextChannel, User
from discord.abc import Messageable
import pytest
from pytest import MonkeyPatch
import pytest_asyncio

from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.config import Config

from .birthday import Birthday
from .core import Core


class TestRed(Red):
    """This class is a hack that lets us set values to getter-only properties."""

    # Define getter-only properties here and override class signature of an instance
    # by setting its __class__ to this class.
    user: Optional[ClientUser] = None
    guilds: Sequence[Guild] = []


@pytest_asyncio.fixture()
async def cogBirthday(
    monkeypatch: MonkeyPatch,
    red: Red,
    event_loop: AbstractEventLoop,
) -> AsyncGenerator[Birthday, None]:
    """A fixture of `Birthday` loaded by a Red instance.
    Note that the background task of the cog provided by this fixture does not run upon cog instantiation.
    """

    red.loop = event_loop

    with monkeypatch.context() as patchContext:
        # In test environments, we intentionally disable
        # the background task of the cog to avoid the
        # coroutine being unexpectedly terminated when
        # the test session completes. If the background
        # task needs to be tested, then method birthdayLoop
        # can be examined accordingly.
        patchContext.setattr(target=Core, name="birthdayLoop", value=mock.AsyncMock())
        await red.add_cog(Birthday(bot=red))

    cog = red.get_cog(Birthday.__name__)
    assert isinstance(cog, Birthday)

    cog.bgTask.cancel()

    yield cog

    await red.remove_cog(Birthday.__name__)


@pytest.fixture()
def mockClientUser(
    mockClientUserWith: Callable[..., Union[mock.Mock, ClientUser]],
) -> Union[mock.Mock, ClientUser]:
    return mockClientUserWith()


@pytest.fixture()
def mockClientUserWith() -> Callable[..., Union[mock.Mock, ClientUser]]:
    def factoryFn(**kwargs) -> Union[mock.Mock, ClientUser]:
        clientUser = mock.create_autospec(spec=ClientUser)
        clientUser.id = 39 ^ abs(hash(ClientUser.__name__))
        clientUser.configure_mock(**kwargs)
        return clientUser

    return factoryFn


@pytest.fixture()
def mockContext(mockUser: User) -> Union[mock.Mock, Context]:
    ctx = mock.Mock()
    ctx.author = mockUser
    ctx.channel = mock.create_autospec(spec=Messageable)
    ctx.clean_prefix = "[p]"
    ctx.send = mock.AsyncMock()
    return ctx


@pytest.fixture()
def mockGuild() -> Union[mock.Mock, Guild]:
    guild = mock.create_autospec(spec=Guild)
    guild.id = 39 ^ abs(hash(Guild.__name__))
    return guild


@pytest.fixture()
def mockMember(
    mockMemberWith: Callable[..., Union[mock.Mock, Member]],
) -> Union[mock.Mock, Member]:
    return mockMemberWith()


@pytest.fixture()
def mockMemberWith(mockGuild: Guild) -> Callable[..., Union[mock.Mock, Member]]:
    def factoryFn(**kwargs) -> Union[mock.Mock, Member]:
        member = mock.create_autospec(spec=Member)
        member.id = 39 ^ abs(hash(Member.__name__))
        member.guild = mockGuild
        member.configure_mock(**kwargs)
        return member

    return factoryFn


@pytest.fixture()
def mockRole(mockGuild: Guild) -> Union[mock.Mock, Role]:
    role = mock.create_autospec(spec=Role)
    role.id = 39 ^ abs(hash(Role.__name__))
    role.guild = mockGuild
    return role


@pytest.fixture()
def mockTextChannel(mockGuild: Guild) -> Union[mock.Mock, TextChannel]:
    textChannel = mock.create_autospec(spec=TextChannel)
    textChannel.id = 39 ^ abs(hash(TextChannel.__name__))
    textChannel.guild = mockGuild
    return textChannel


@pytest.fixture()
def mockUser(
    mockUserWith: Callable[..., Union[mock.Mock, User]],
) -> Union[mock.Mock, User]:
    return mockUserWith()


@pytest.fixture()
def mockUserWith(mockGuild: Guild) -> Callable[..., Union[mock.Mock, User]]:
    def factoryFn(**kwargs) -> Union[mock.Mock, User]:
        user = mock.create_autospec(spec=User)
        user.id = 39 ^ abs(hash(User.__name__))
        user.guild = mockGuild
        user.configure_mock(**kwargs)
        return user

    return factoryFn


@pytest_asyncio.fixture()
async def red(monkeypatch: MonkeyPatch, red: Red, mockClientUser: ClientUser):
    with monkeypatch.context() as patchContext:
        patchContext.setattr(
            target=red,
            name="__class__",
            value=TestRed,
        )
        patchContext.setattr(
            target=red,
            name="user",
            value=mockClientUser,
        )
        yield red


@pytest.fixture(autouse=True)
def __get_conf_setup(
    monkeypatch: MonkeyPatch,
    config_fr: Config,
) -> Generator[None, None, None]:
    with monkeypatch.context() as patchContext:
        patchContext.setattr(
            target=Config,
            name="get_conf",
            value=mock.Mock(return_value=config_fr),
        )
        yield


@pytest.fixture(autouse=True)
def __locale_setup() -> Generator[None, None, None]:
    previousTimeLocale = locale.getlocale(category=locale.LC_TIME)
    locale.setlocale(category=locale.LC_TIME, locale=("en", "UTF-8"))
    try:
        yield
    finally:
        locale.setlocale(category=locale.LC_TIME, locale=previousTimeLocale)
