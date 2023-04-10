# Heartbeat
This cog allows a bot owner to punch a heartbeat to an uptime checker. You can pair
this with a webhook channel on a Discord server to receive notifications when your
bot doesn't punch a heartbeat in time.

# Getting started
The creator of this cog uses [StatusCake], so this guide assumes that you will be
using it as well.

This guide assumes your bot prefix is `ren`.

As the [StatusCake] UI may update at any time, please open a PR to fix any steps
should you discover any discrepancies.

## Prerequisites
- A [StatusCake] account.
- A Discord webhook URL.
- The `heartbeat` cog is loaded.

## Steps to configure [StatusCake]
1. Log in to [StatusCake].
2. Under the **Alerting** section, select **Integrations**.
3. In the **Add New 3rd Party Service** section, select **Discord** in the Type
   dropdown menu.
4. Fill in the following, then click **Save Integration**:
    - Name: `Discord Heartbeat Webhook` (for your easy reference).
    - Webhook: The Discord webhook URL.
5. In the **Your 3rd Party Accounts** section, find the integration you just added,
   and click the **Send Test** button (the paper airplane icon). Ensure that the
   webhook you pasted earlier received a notification.
6. Under the **Alerting** section, select **Contact Groups** > **New Contact Group**.
7. Fill in the following, then click **Save Now**:
    - Group Name: `Discord Heartbeat Notifications` (for your easy reference).
    - Integration: Select `Discord Heartbeat Webhook`.
8. In the **Uptime** section, click **New Uptime Tests**.
9. Fill in the following, then click **Create test**:
    - Test Type: Select `PUSH`.
    - Push Period: `60` seconds.
    - Test Name: _Something descriptive, of your choosing_.
    - Contact Groups: Select `Discord Heartbeat Notifications`.
10. Select **Push Tests** at the top, and find the test you just created.
11. Click **View Detailed Test Information** (the `i` icon).
12. At the top, there is a URL that starts with `https://push.statuscake.com/`. Make
    a note of this URL.


## Steps to configure the heartbeat cog
1. In a DM to your bot, send the following:
    - `renhbset interval 50`.
    - `renhbset url PUSH_URL`, where `PUSH_URL` is the one from step 12 in the
      previous section.
    - `renhbset name INSTANCE_NAME`, where `INSTANCE_NAME` is whatever you want.
2. Reload the heartbeat cog.
3. You should be good to go!

[StatusCake]: https://statuscake.com/
