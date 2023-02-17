<p align=center><img src="ren.png" height="200" width="200"></p1>

# SFU Anime Club - Ren
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

**Ren Kitagawa**, or **Ren** for short, is one of SFU Anime Club's mascots, and is
also our main Discord bot. She is a forked version of [Red-DiscordBot v3]. The main
differences between this project and the upstream project include:
- Bundling some of our cogs from the [Injabie3/lui-cogs-v3] repo that we're using.
- Making some changes to Alias to use it in conjunction with our Tags cog.
- Including some third-party cogs we're using in source control.

The addition of cogs (the root `cogs/` directory) was done to make creating an
instance of the same bot that the club uses easier; however, we have started adding
third-party cog repos instead by using the Downloader cog.

# Contribute
We welcome changes that benefit the server as a whole! Please feel free to submit any
suggestions via the [SFU Anime Club feedback form] about your ideas. You may also
feel free to reach out to someone on the SFU Anime Club Discord server to discuss!

# Installation
Please consult the original forked README [here](README_upstream.md) for more details.

Once completed, add the `cogs/` directory to your bot's cog path using the
`[p]addpath` command.

# License
As per the upstream license, this project is [GNU GPL v3](LICENSE).

Contents in the root `cogs/` directory follow that in the [Injabie3/lui-cogs-v3] repo
for cogs that appear in that cog repo, otherwise a separate license file should be
included for third party cogs.

[Red-DiscordBot v3]: https://github.com/Cog-Creators/Red-DiscordBot
[Injabie3/lui-cogs-v3]: https://github.com/Injabie3/lui-cogs-v3
[SFU Anime Club feedback form]: https://u.sfuani.me/feedback
