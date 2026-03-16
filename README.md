# AI Creator Intel

[English README](./README.en.md)

一个面向 OpenClaw 的 AI 创作者情报 skill，聚合 `Twitter/X`、`AI 新闻` 和 `AIGC 比赛信息`，输出适合内容创作者消费的日报或周报。

这个 skill 的核心目标不是“抓得越多越好”，而是：

- 优先一手信息
- 优先创作者真正会用到的内容
- 降低泛资讯和重复信息的噪音

## 这个 skill 能做什么

它把三条信息流合成一份 brief：

1. `Twitter/X` 账号池监控
2. `AI 新闻` 聚合与过滤
3. `AIGC 比赛` 跟踪

默认输出栏目：

- `must_know_launches`
- `builder_moves`
- `creator_workflows`
- `viral_aigc`
- `watch_next`
- `contest_opportunities`

## 当前 V1 设计思路

这一版是 `watchlist-first`：

- `Twitter/X` 以人工维护账号池为主，不把全网发现当主链路
- `新闻` 优先官方和稳定来源
- `比赛` 优先创作者相关的聚合页和官方页面

这样做的目的，是让结果更像“AI 内容博主的情报台”，而不是一个泛 AI 新闻爬虫。

## 当前包含的来源

### Twitter/X

- 已维护 `core`、`candidate`、`scout` 三层账号池
- 支持浏览器模式抓取真实 watchlist
- 也预留了 API 路线，但不是当前主路径

### 新闻

当前 live 默认新闻源包括：

- OpenAI News
- Anthropic News
- Google DeepMind Blog
- Perplexity Hub Blog
- Runway News
- ElevenLabs Blog
- Product Hunt
- GitHub Trending
- Hacker News

### 比赛

当前比赛链路优先：

- AIBetas AIGC 赛事页
- 以及 `config/contest-sources.yaml` 里配置的补充发现源

## 仓库结构

```text
ai-creator-intel/
├── SKILL.md
├── README.md
├── README.en.md
├── agents/
├── assets/
├── config/
├── references/
├── sample-data/
├── scripts/
└── tests/
```

关键文件：

- [`SKILL.md`](./SKILL.md)：skill 的行为说明和使用规则
- [`config/twitter-watchlist.yaml`](./config/twitter-watchlist.yaml)：Twitter/X 账号池
- [`config/twitter-fetch-config.yaml`](./config/twitter-fetch-config.yaml)：抓取、过滤、打分策略
- [`config/news-sources.yaml`](./config/news-sources.yaml)：新闻源配置和优先级
- [`config/contest-sources.yaml`](./config/contest-sources.yaml)：比赛源配置

## 快速开始

### 1. 先校验配置

```bash
python3 scripts/validate_configs.py
```

### 2. 只跑新闻

```bash
python3 scripts/build_news_brief.py 'news://default' daily_brief
```

### 3. 只跑比赛

```bash
python3 scripts/build_contest_brief.py 'https://www.aibetas.com.cn/aigc-events' daily_brief --render
```

### 4. 跑完整 brief

```bash
python3 scripts/build_full_brief.py \
  --mode daily_brief \
  --twitter-source 'xbrowser://watchlist' \
  --news-source 'news://default' \
  --contest-source 'https://www.aibetas.com.cn/aigc-events' \
  --render
```

## Twitter/X 使用方式

生产环境推荐用浏览器模式。

先初始化一个持久化、已登录的 X profile：

```bash
python3 scripts/init_x_browser_profile.py --profile-dir /path/to/x-profile
```

然后导出环境变量：

```bash
export X_BROWSER_PROFILE_DIR="/path/to/x-profile"
```

当前浏览器模式会：

- 读取 `core + candidate`
- 保留 `original + quote + repost`
- 排除 replies
- 抓最近 24 小时窗口，并带滚动保护

## 开发说明

这个仓库里已经包含：

- 本地开发用 sample data
- 各条链路的 parser 和 brief 组装脚本
- Twitter/X、新闻、比赛、full brief 的测试

跑测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 生产试跑

正式接飞书或邮件之前，先按这份清单跑第一轮：

- [`references/production-trial-checklist.md`](./references/production-trial-checklist.md)

建议顺序：

1. 先跑 Twitter/X
2. 再跑新闻
3. 再跑比赛
4. 最后跑完整 brief

只有在本地输出已经像样之后，再接最终投递。

## 当前 V1 限制

- Twitter/X 仍然依赖浏览器会话或第三方 API
- 部分比赛条目字段还不够完整
- 新闻过滤现在偏“创作者实用性”，不是全量行业收录
- 为了避免噪音，source 扩张策略比较保守

## License

MIT。见 [`LICENSE`](LICENSE)。
