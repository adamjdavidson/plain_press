# Sources: Where to Find Amish-Appropriate Stories

## Source Strategy Overview

The system uses two complementary approaches:

1. **Curated RSS Feeds**: Reliable publications that consistently produce appropriate content. These provide a steady baseline.

2. **AI-Powered Web Search**: Broader searches via Exa API to catch oddball stories that don't come from predictable places. These surface the surprising gems.

Both streams feed into the AI filter, which applies the story criteria before presenting candidates to Adam.

---

## Tier 1: Oddball/Quirky News

These are the core sources—publications specifically focused on unusual, surprising news.

### UPI Odd News
- **URL**: https://www.upi.com/Odd_News/
- **RSS**: Available
- **Notes**: Adam's proven source. Wire service quality. Wide variety—animals, local oddities, quirky products. Global reach.
- **Caution**: Occasionally includes individual achievement stories or stories adjacent to tragedy.

### AP Oddities
- **URL**: https://apnews.com/oddities
- **RSS**: Available
- **Notes**: Associated Press wire service. Reliable, fact-checked. Similar to UPI in scope and quality.
- **Caution**: Same as UPI—needs filtering for individual heroes and tragedy-adjacent content.

### Reuters Oddly Enough
- **URL**: https://www.reuters.com/lifestyle/oddly-enough/
- **RSS**: Available
- **Notes**: Third major wire service. More international flavor than UPI/AP. Good for global oddities.
- **Caution**: Occasionally more sophisticated/urban in sensibility.

### Sky News Offbeat
- **URL**: https://news.sky.com/offbeat
- **RSS**: Available
- **Notes**: UK-focused. Strong on animal stories, British quirkiness. Good cultural variety.
- **Caution**: UK-specific references may need context.

### News of the Weird
- **URL**: Syndicated column (appears in various papers)
- **Notes**: Long-running curated column. Pre-filtered for weirdness. Chuck Shepherd's original, now continued by Andrews McMeel Syndication.
- **Caution**: Can lean darker/edgier than appropriate. Needs careful filtering.

---

## Tier 2: Positive/Wholesome News

These publications focus on uplifting content. Higher hit rate for tone, but watch for individual hero stories.

### Good News Network
- **URL**: https://www.goodnewsnetwork.org/
- **RSS**: Available
- **Notes**: 21,000+ story archive. Categories include Animals, Earth, Inspiring, Laughs. Been running since 1997.
- **Caution**: Heavy on "hero" stories—individuals doing remarkable things. These conflict with Amish modesty values. Filter carefully.
- **Best sections**: Animals, Laughs, Earth

### Positive News
- **URL**: https://www.positive.news/
- **RSS**: Available
- **Notes**: UK-based. More thoughtful, less viral-chasing. Categories include Society, Environment, Lifestyle.
- **Caution**: Can be too focused on social change, activism. Filter for political content.
- **Best sections**: Lifestyle, Arts

### DailyGood
- **URL**: https://www.dailygood.org/
- **RSS**: Available
- **Notes**: Volunteer-run for 25+ years. 140,000+ subscribers. Curated daily selections.
- **Caution**: Sometimes spiritual/philosophical in ways that may not align with conservative Christian values.

### Good Good Good
- **URL**: https://www.goodgoodgood.co/
- **RSS**: Available
- **Notes**: Tagline is "real good news, not just feel good news." Weekly roundups.
- **Caution**: Progressive editorial slant. Filter for political content.

### Sunny Skyz
- **URL**: https://www.sunnyskyz.com/good-news
- **RSS**: Available
- **Notes**: Aggregator of positive news from other sources.
- **Caution**: Quality varies. Some stories are repackaged clickbait.

### CBS The Uplift
- **URL**: https://www.cbsnews.com/uplift/
- **Notes**: Video-heavy, but provides story leads. Mainstream appeal, family-friendly.
- **Caution**: May require extracting print story from video content.

---

## Tier 3: Animal-Focused Sources

Animals are the most reliable category. These sources specialize in animal content.

### NBC Animal News
- **URL**: https://www.nbcnews.com/animal-news
- **Notes**: Mainstream news outlet's animal vertical. Wide variety—pets, wildlife, conservation.
- **Caution**: Conservation stories can veer into environmental doom. Filter carefully.

### Farm Sanctuary News & Stories
- **URL**: https://www.farmsanctuary.org/news-stories/
- **Notes**: Focus on farm animal rescue stories. Very aligned with wholesome, community values.
- **Caution**: Some stories involve animal suffering (before rescue). Focus on the rescue, not the hardship.

### The Dodo
- **URL**: https://www.thedodo.com/
- **Notes**: Very popular animal content. Viral potential.
- **Caution**: Heavily video-based. May need to extract story leads. Can be emotionally manipulative.

---

## Tier 4: Food Industry

Strange food products are reliably surprising and wholesome.

### FoodBev.com
- **URL**: https://www.foodbev.com/
- **Notes**: Industry trade publication. Covers new product launches, weird flavors, food innovations.
- **Caution**: Industry jargon. May need translation for general audience.
- **Best sections**: New products, Innovations

### Food Processing - Rollout Section
- **URL**: https://www.foodprocessing.com/new-food-products/
- **Notes**: Monthly roundups of new food products. Good for discovering strange flavor combinations.
- **Caution**: Trade publication format. Dry language.

### Eater (selective)
- **URL**: https://www.eater.com/
- **Notes**: Food media publication. Trend pieces can surface weird food stories.
- **Caution**: Urban/foodie sensibility. Restaurant reviews not relevant. Look for weird trend pieces only.

---

## Tier 5: Specialized/Niche Sources

For specific topic areas that consistently produce appropriate content.

### Covered Bridge Sources
- Parke County Covered Bridge Festival: https://www.coveredbridges.com/
- Various state covered bridge societies
- **Notes**: Covered bridges are perfect Amish content—heritage, craftsmanship, community celebration.

### Heritage Railway Publications
- Trains Magazine (selective): https://www.trains.com/
- Various heritage railway society newsletters
- **Notes**: Steam trains, volunteer restoration, nostalgia. Good community angles.

### Atlas Obscura
- **URL**: https://www.atlasobscura.com/
- **Notes**: Unusual places, hidden wonders, quirky locations. Strong "isn't that something!" factor.
- **Caution**: Can be too "cool" or ironic in tone. Some destinations involve modern attractions.
- **Best sections**: Food, Places (rural/historical), Unusual Discoveries

---

## Search Queries for Exa API

In addition to RSS feeds, the system should run regular searches. Effective query patterns:

### Community/Cooperation Queries
- `community builds bridge volunteers`
- `neighbors help neighbors project`
- `town comes together celebration`
- `volunteers restore historic`
- `barn raising community`

### Animal Queries
- `unusual animal behavior heartwarming`
- `unlikely animal friendship`
- `farm animal rescue`
- `pet quirky habit`
- `animal unexpected place`

### Food Queries
- `bizarre food product launch`
- `unusual flavor combination`
- `strange food trend`
- `giant vegetable harvest`

### Heritage/Tradition Queries
- `covered bridge festival`
- `historic mill restored`
- `water wheel working`
- `steam train heritage railway`
- `traditional craftsman`

### Oddity Queries
- `quirky small town tradition`
- `unusual discovery`
- `world's smallest` (for places/things, not human records)
- `world's largest` (same caveat)
- `miniature village model`

### Queries to Avoid
- Anything including "hero," "saves," "breaks record" (for humans)
- Anything including technology terms
- Anything including "viral," "TikTok," "social media"

---

## Source Scoring

Over time, the system should track which sources produce approved articles and adjust accordingly.

**Metrics to track per source:**
- Total articles surfaced
- Articles rated "Good"
- Articles rated "No"
- Articles with "Why Not" feedback
- Approval rate (Good / Total)

**Weekly adjustments:**
- Sources with high approval rate: Search more frequently, weight higher
- Sources with low approval rate: Reduce frequency, flag for review
- Sources with zero approvals over 2+ weeks: Consider removing

---

## Adding New Sources

When Adam or the system identifies a promising new source:

1. Add to sources database with default neutral weighting
2. Monitor for 2 weeks
3. Evaluate approval rate
4. Adjust weighting or remove

The system should occasionally search for new source candidates:
- "odd news sites"
- "positive news publications"
- "wholesome news sources"
- Regional newspaper "odd news" sections
