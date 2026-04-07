# Track team usage with analytics

> Source: https://code.claude.com/docs/en/analytics

> View Claude Code usage metrics, track adoption, and measure engineering velocity in the analytics dashboard.

Claude Code provides analytics dashboards to help organizations understand developer usage patterns, track contribution metrics, and measure how Claude Code impacts engineering velocity.

| Plan                          | Dashboard URL                                                              | Includes                                                                              |
| ----------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Claude for Teams / Enterprise | [claude.ai/analytics/claude-code](https://claude.ai/analytics/claude-code) | Usage metrics, contribution metrics with GitHub integration, leaderboard, data export |
| API (Claude Console)          | [platform.claude.com/claude-code](https://platform.claude.com/claude-code) | Usage metrics, spend tracking, team insights                                          |

## Access analytics for Team and Enterprise

Navigate to [claude.ai/analytics/claude-code](https://claude.ai/analytics/claude-code). Admins and Owners can view the dashboard.

The Team and Enterprise dashboard includes:

* **Usage metrics**: lines of code accepted, suggestion accept rate, daily active users and sessions
* **Contribution metrics**: PRs and lines of code shipped with Claude Code assistance, with GitHub integration
* **Leaderboard**: top contributors ranked by Claude Code usage
* **Data export**: download contribution data as CSV for custom reporting

### Enable contribution metrics

Contribution metrics are in public beta and available on Claude for Teams and Claude for Enterprise plans. These metrics only cover users within your claude.ai organization.

Usage and adoption data is available for all Claude for Teams and Claude for Enterprise accounts. Contribution metrics require additional setup to connect your GitHub organization.

You need the Owner role to configure analytics settings. A GitHub admin must install the GitHub app.

Contribution metrics are not available for organizations with Zero Data Retention enabled.

1. **Install the GitHub app**: A GitHub admin installs the Claude GitHub app on your organization's GitHub account at [github.com/apps/claude](https://github.com/apps/claude).
2. **Enable Claude Code analytics**: A Claude Owner navigates to [claude.ai/admin-settings/claude-code](https://claude.ai/admin-settings/claude-code) and enables the Claude Code analytics feature.
3. **Enable GitHub analytics**: On the same page, enable the "GitHub analytics" toggle.
4. **Authenticate with GitHub**: Complete the GitHub authentication flow and select which GitHub organizations to include in the analysis.

Data typically appears within 24 hours after enabling, with daily updates.

Contribution metrics support GitHub Cloud and GitHub Enterprise Server.

### Review summary metrics

These metrics are deliberately conservative and represent an underestimate of Claude Code's actual impact.

The dashboard displays these summary metrics at the top:

* **PRs with CC**: total count of merged pull requests that contain at least one line of code written with Claude Code
* **Lines of code with CC**: total lines of code across all merged PRs that were written with Claude Code assistance. Only "effective lines" are counted.
* **PRs with Claude Code (%)**: percentage of all merged PRs that contain Claude Code-assisted code
* **Suggestion accept rate**: percentage of times users accept Claude Code's code editing suggestions
* **Lines of code accepted**: total lines of code written by Claude Code that users have accepted in their sessions

### Explore the charts

#### Track adoption

The Adoption chart shows daily usage trends:

* **users**: daily active users
* **sessions**: number of active Claude Code sessions per day

#### Measure PRs per user

* **PRs per user**: total number of PRs merged per day divided by daily active users
* **users**: daily active users

#### View pull requests breakdown

The Pull requests chart shows a daily breakdown of merged PRs:

* **PRs with CC**: pull requests containing Claude Code-assisted code
* **PRs without CC**: pull requests without Claude Code-assisted code

Toggle to **Lines of code** view to see the same breakdown by lines of code rather than PR count.

#### Find top contributors

The Leaderboard shows the top 10 users ranked by contribution volume. Toggle between Pull requests and Lines of code views.

Click **Export all users** to download complete contribution data for all users as a CSV file.

### PR attribution

When contribution metrics are enabled, Claude Code analyzes merged pull requests to determine which code was written with Claude Code assistance.

#### Tagging criteria

PRs are tagged as "with Claude Code" if they contain at least one line of code written during a Claude Code session.

#### Attribution process

When a pull request is merged:

1. Added lines are extracted from the PR diff
2. Claude Code sessions that edited matching files within a time window are identified
3. PR lines are matched against Claude Code output using multiple strategies
4. Metrics are calculated for AI-assisted lines and total lines

Merged pull requests containing Claude Code-assisted lines are labeled as `claude-code-assisted` in GitHub.

#### Time window

Sessions from 21 days before to 2 days after the PR merge date are considered for attribution matching.

#### Excluded files

Certain files are automatically excluded from analysis: lock files, generated code, build directories, test fixtures, and lines over 1,000 characters.

#### Attribution notes

* Code substantially rewritten by developers (more than 20% difference) is not attributed to Claude Code
* Sessions outside the 21-day window are not considered
* The algorithm does not consider the PR source or destination branch

### Get the most from analytics

#### Monitor adoption

Track the Adoption chart and user counts to identify active users, overall adoption trends, and dips in usage.

#### Measure ROI

* Track changes in PRs per user over time as adoption increases
* Compare PRs and lines of code shipped with vs. without Claude Code
* Use alongside DORA metrics, sprint velocity, or other engineering KPIs

#### Identify power users

The Leaderboard helps you find team members with high Claude Code adoption who can share techniques, provide feedback, and help onboard new users.

#### Access data programmatically

Search for PRs labeled with `claude-code-assisted` in GitHub.

## Access analytics for API customers

API customers using the Claude Console can access analytics at [platform.claude.com/claude-code](https://platform.claude.com/claude-code). You need the UsageView permission.

The Console dashboard displays:

* **Lines of code accepted**: total lines of code written by Claude Code that users have accepted
* **Suggestion accept rate**: percentage of times users accept code editing tool usage
* **Activity**: daily active users and sessions shown on a chart
* **Spend**: daily API costs in dollars alongside user count

### View team insights

The team insights table shows per-user metrics:

* **Members**: all users who have authenticated to Claude Code
* **Spend this month**: per-user total API costs for the current month
* **Lines this month**: per-user total of accepted code lines for the current month

## Related resources

* [Monitoring with OpenTelemetry](/en/monitoring-usage): export real-time metrics and events to your observability stack
* [Manage costs effectively](/en/costs): set spend limits and optimize token usage
* [Permissions](/en/permissions): configure roles and permissions
