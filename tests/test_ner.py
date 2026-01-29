"""Tests for NER extraction."""

import pytest

from sherlockml.ml.ner_extractor import NERExtractor


class TestNERExtractor:
    """Test suite for NER extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create NER extractor instance."""
        return NERExtractor()
    
    def test_flag_extraction(self, extractor, sample_ctf_text):
        """Test CTF flag extraction."""
        entities = extractor.extract(sample_ctf_text)
        
        assert len(entities.flags) >= 2
        assert any("s3cr3t" in f for f in entities.flags)
        assert any("CTF{" in f for f in entities.flags)
    
    def test_email_extraction(self, extractor, sample_ctf_text):
        """Test email extraction."""
        entities = extractor.extract(sample_ctf_text)
        
        assert "user@ctfchallenge.com" in entities.emails
    
    def test_hash_extraction(self, extractor, sample_ctf_text):
        """Test hash extraction."""
        entities = extractor.extract(sample_ctf_text)
        
        # SHA1 hash
        assert any(len(h) == 40 for h in entities.hashes)
    
    def test_username_extraction(self, extractor, sample_ctf_text):
        """Test username extraction."""
        entities = extractor.extract(sample_ctf_text)
        
        # Should find @ctf_player_1337 and github.com/ctfplayer
        assert any("ctf" in u.lower() for u in entities.usernames)
    
    def test_find_flags_method(self, extractor):
        """Test convenience find_flags method."""
        text = "The answer is flag{simple_test}"
        flags = extractor.find_flags(text)
        
        assert len(flags) >= 1
        assert "flag{simple_test}" in flags
    
    def test_various_flag_formats(self, extractor):
        """Test various CTF flag formats."""
        text = """
        flag{standard}
        CTF{uppercase}
        picoCTF{pico_format}
        HTB{hackthebox}
        hxp{hxp_ctf}
        """
        flags = extractor.find_flags(text)
        
        assert len(flags) >= 4
    
    def test_empty_text(self, extractor):
        """Test extraction from empty text."""
        entities = extractor.extract("")
        
        assert len(entities.flags) == 0
        assert len(entities.emails) == 0
    
    def test_url_extraction(self, extractor):
        """Test URL extraction."""
        text = "Check https://example.com/profile and http://test.org"
        entities = extractor.extract(text)
        
        assert len(entities.urls) >= 2
    
    def test_ip_extraction(self, extractor):
        """Test IP address extraction."""
        text = "Server at 192.168.1.1 and backup at 10.0.0.1"
        entities = extractor.extract(text)
        
        assert "192.168.1.1" in entities.ips
        assert "10.0.0.1" in entities.ips
    
    def test_to_dict(self, extractor, sample_ctf_text):
        """Test conversion to dictionary."""
        entities = extractor.extract(sample_ctf_text)
        result = entities.to_dict()
        
        assert "flags" in result
        assert "emails" in result
        assert "hashes" in result
        assert isinstance(result["flags"], list)
