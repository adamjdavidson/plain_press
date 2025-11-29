"""
Integration tests for Story Quality Filter feature.

Tests the content type classification, wow factor scoring, and rejection reason formatting.
These tests require the Claude API to be configured (via ANTHROPIC_API_KEY env var).
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# Skip all tests if no API key available (for CI environments)
pytestmark = pytest.mark.skipif(
    not os.environ.get('ANTHROPIC_API_KEY'),
    reason="ANTHROPIC_API_KEY not set - skipping Claude API tests"
)


class TestContentTypeFiltering:
    """Tests for User Story 1: Filter Out Non-News Content"""
    
    def test_event_listing_rejected(self):
        """Event listings should be rejected with content_type=event_listing and score 0.0"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "Fall Festival 2025 - Buy Tickets Now!",
            "content": "Join us October 15-17 for the annual Fall Festival! Tickets on sale now. "
                      "Activities include: pumpkin carving, hayrides, corn maze, and live music. "
                      "Adults $15, children $8. Gates open at 10am."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        assert len(discarded) == 1, "Event listing should be discarded"
        assert len(kept) == 0, "Event listing should not be kept"
        assert discarded[0]['content_type'] == 'event_listing', \
            f"Expected content_type='event_listing', got '{discarded[0].get('content_type')}'"
        assert discarded[0]['filter_score'] == 0.0, \
            f"Expected filter_score=0.0, got {discarded[0].get('filter_score')}"
    
    def test_about_page_rejected(self):
        """About pages should be rejected with content_type=about_page and score 0.0"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "About Our Farm - Meet the Johnson Family",
            "content": "Welcome to Johnson Family Farm! We've been farming this land since 1952. "
                      "Our mission is to provide fresh, locally grown produce to our community. "
                      "The farm spans 200 acres and is now run by the third generation of Johnsons."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        assert len(discarded) == 1, "About page should be discarded"
        assert len(kept) == 0, "About page should not be kept"
        assert discarded[0]['content_type'] == 'about_page', \
            f"Expected content_type='about_page', got '{discarded[0].get('content_type')}'"
        assert discarded[0]['filter_score'] == 0.0
    
    def test_directory_page_rejected(self):
        """Directory pages should be rejected with content_type=directory_page and score 0.0"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "Meet Our Therapy Animals",
            "content": "Our therapy animal team includes: Bella (golden retriever), "
                      "Max (labrador), Luna (therapy cat), Charlie (miniature horse). "
                      "Each animal is certified and available for facility visits. "
                      "Contact us to schedule a visit."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        assert len(discarded) == 1, "Directory page should be discarded"
        assert len(kept) == 0, "Directory page should not be kept"
        assert discarded[0]['content_type'] == 'directory_page', \
            f"Expected content_type='directory_page', got '{discarded[0].get('content_type')}'"
        assert discarded[0]['filter_score'] == 0.0
    
    def test_news_article_passes_content_check(self):
        """Actual news articles should get content_type=news_article"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "Giant Pumpkin Breaks County Record at Annual Fair",
            "content": "A 1,247-pound pumpkin grown by local farmer Tom Henderson won first place "
                      "at yesterday's county fair, breaking the previous record by 89 pounds. "
                      "Henderson said he used a special composting technique passed down from his grandfather. "
                      "The winning pumpkin will be displayed at the town square through October."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        # The article should be classified as news_article
        all_articles = kept + discarded
        assert len(all_articles) == 1
        assert all_articles[0]['content_type'] == 'news_article', \
            f"Expected content_type='news_article', got '{all_articles[0].get('content_type')}'"


class TestWowFactorFiltering:
    """Tests for User Story 2: Reject Boring/Mundane News"""
    
    def test_boring_news_low_wow_score(self):
        """Mundane news should receive a low wow_score"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "City Council Approves Annual Budget",
            "content": "The city council voted 5-2 to approve the annual budget of $4.2 million "
                      "at Tuesday's meeting. The budget includes funding for road maintenance, "
                      "parks department, and administrative costs. Mayor Smith said the budget "
                      "reflects the city's priorities for the coming fiscal year."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        all_articles = kept + discarded
        assert len(all_articles) == 1
        
        # This should be classified as news but with low wow_score
        article = all_articles[0]
        if article['content_type'] == 'news_article':
            assert 'wow_score' in article, "wow_score should be present for news articles"
            assert article['wow_score'] < 0.5, \
                f"Boring news should have low wow_score, got {article.get('wow_score')}"
    
    def test_wow_news_high_wow_score(self):
        """Surprising/delightful news should receive a high wow_score"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "Sheep Wearing Tiny Sweaters Escape Farm, Parade Through Downtown",
            "content": "Residents of Millbrook were treated to an unusual sight yesterday when "
                      "a flock of 12 sheep, each wearing a hand-knitted sweater, escaped from "
                      "the Henderson farm and paraded down Main Street. The sheep had been dressed "
                      "for a photo shoot but got out when a gate was left open. Locals helped "
                      "guide the woolly parade back home with no injuries reported."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        all_articles = kept + discarded
        assert len(all_articles) == 1
        
        article = all_articles[0]
        assert article['content_type'] == 'news_article', \
            f"Should be classified as news_article, got '{article.get('content_type')}'"
        assert 'wow_score' in article, "wow_score should be present"
        assert article['wow_score'] >= 0.5, \
            f"Delightful news should have high wow_score, got {article.get('wow_score')}"
    
    def test_wow_threshold_rejection(self):
        """Articles below WOW_SCORE_THRESHOLD should be rejected"""
        from app.services.claude_filter import filter_all_articles, WOW_SCORE_THRESHOLD
        
        # Test with a clearly mundane news story
        articles = [{
            "headline": "New Stop Sign Installed at Oak Street Intersection",
            "content": "The town installed a new stop sign at the intersection of Oak Street "
                      "and Maple Avenue on Monday. Public Works Director Bob Johnson said the "
                      "sign was needed due to increased traffic in the area. Drivers are reminded "
                      "to come to a complete stop."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        # If classified as news, it should be rejected for low wow_score
        all_articles = kept + discarded
        if all_articles and all_articles[0]['content_type'] == 'news_article':
            article = all_articles[0]
            if article.get('wow_score', 0) < WOW_SCORE_THRESHOLD:
                assert article in discarded, \
                    "Article with wow_score below threshold should be discarded"
                assert "wow_score=" in article.get('filter_notes', ''), \
                    "Rejection reason should mention wow_score"


class TestRejectionReasonFormat:
    """Tests for User Story 3: Clear Rejection Reasons"""
    
    def test_content_type_rejection_reason_format(self):
        """Content type rejections should have clear format: 'Rejected: content_type=...'"""
        from app.services.claude_filter import filter_all_articles
        
        articles = [{
            "headline": "Annual Bake Sale - This Saturday!",
            "content": "Don't miss our annual church bake sale this Saturday from 9am-2pm. "
                      "Homemade pies, cookies, and cakes. All proceeds benefit the youth group."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        assert len(discarded) >= 1, "Event listing should be discarded"
        
        article = discarded[0]
        filter_notes = article.get('filter_notes', '')
        assert 'Rejected: content_type=' in filter_notes, \
            f"filter_notes should contain 'Rejected: content_type=', got: {filter_notes}"
    
    def test_wow_score_rejection_reason_format(self):
        """Wow score rejections should have format: 'Rejected: wow_score=X.XX (threshold: Y.YY)'"""
        from app.services.claude_filter import filter_all_articles, WOW_SCORE_THRESHOLD
        
        articles = [{
            "headline": "Local Library Extends Hours",
            "content": "Starting next month, the public library will extend its hours on Tuesdays "
                      "and Thursdays, staying open until 8pm instead of 6pm. Library director "
                      "Sarah Mills said the change responds to community requests."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        all_articles = kept + discarded
        if all_articles and all_articles[0]['content_type'] == 'news_article':
            article = all_articles[0]
            if article.get('wow_score', 0) < WOW_SCORE_THRESHOLD:
                filter_notes = article.get('filter_notes', '')
                assert 'wow_score=' in filter_notes, \
                    f"Low wow_score rejection should mention wow_score in filter_notes: {filter_notes}"
                assert 'threshold' in filter_notes.lower(), \
                    f"Should mention threshold in filter_notes: {filter_notes}"
    
    def test_editorial_rejection_reason_format(self):
        """Editorial rejections should show filter_score and reason"""
        from app.services.claude_filter import filter_all_articles
        
        # Story that should pass content_type and wow checks but fail editorial
        articles = [{
            "headline": "Viral Video Shows Robot Dancing at Tech Conference",
            "content": "A humanoid robot stunned attendees at yesterday's AI Tech Summit by "
                      "performing a perfect breakdance routine. The robot, developed by startup "
                      "TechDance Inc., demonstrated advanced motor control and balance. "
                      "The video has been viewed over 5 million times on social media."
        }]
        
        kept, discarded, stats = filter_all_articles(articles)
        
        # This should be news but rejected for tech content (Amish values)
        all_articles = kept + discarded
        if all_articles:
            article = all_articles[0]
            filter_notes = article.get('filter_notes', '')
            # Should have some explanation of why rejected
            assert len(filter_notes) > 0, "filter_notes should contain rejection reason"

