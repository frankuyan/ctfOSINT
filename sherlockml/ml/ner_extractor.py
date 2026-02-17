"""Named Entity Recognition for CTF-specific entities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import spacy
from spacy.language import Language
from spacy.tokens import Doc


@dataclass 
class ExtractedEntities:
    """Container for extracted named entities."""
    usernames: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    hashes: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    custom: dict[str, list[str]] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, list[str]]:
        """Convert to dictionary."""
        return {
            "usernames": self.usernames,
            "emails": self.emails,
            "flags": self.flags,
            "hashes": self.hashes,
            "projects": self.projects,
            "locations": self.locations,
            "urls": self.urls,
            "ips": self.ips,
            **self.custom,
        }
    
    @property
    def all_entities(self) -> list[str]:
        """Get all extracted entities as a flat list."""
        result = (
            self.usernames + self.emails + self.flags + 
            self.hashes + self.projects + self.locations +
            self.urls + self.ips
        )
        for items in self.custom.values():
            result.extend(items)
        return result


class NERExtractor:
    """Extract CTF-relevant entities from text.
    
    Combines SpaCy NER with custom regex patterns for
    CTF-specific entities like flags, hashes, and usernames.
    
    Entity Types:
        - USERNAME: Social media usernames, handles
        - EMAIL: Email addresses
        - FLAG: CTF flags in various formats
        - HASH: MD5, SHA1, SHA256 hashes
        - PROJECT: GitHub repos, project names
        - LOCATION: Geographic locations
        - URL: Web URLs
        - IP: IP addresses
    
    Example:
        >>> ner = NERExtractor()
        >>> entities = ner.extract("Contact john_doe at john@example.com, flag{s3cr3t}")
        >>> entities.flags
        ['flag{s3cr3t}']
        >>> entities.emails
        ['john@example.com']
    """
    
    # Regex patterns for CTF-specific entities
    PATTERNS = {
        "flags": [
            # Common CTF flag formats
            re.compile(r'(flag|ctf|glug|hxp|picoCTF|HTB|THM|OSCTF)\{[^}]+\}', re.IGNORECASE),
            re.compile(r'FLAG\{[^}]+\}'),
            re.compile(r'CTF\{[^}]+\}'),
            # Base64-encoded flags (require trailing padding)
            re.compile(r'[A-Za-z0-9+/]{40,}={1,2}'),
        ],
        "hashes": [
            # MD5
            re.compile(r'\b[a-fA-F0-9]{32}\b'),
            # SHA1
            re.compile(r'\b[a-fA-F0-9]{40}\b'),
            # SHA256
            re.compile(r'\b[a-fA-F0-9]{64}\b'),
        ],
        "emails": [
            re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        ],
        "urls": [
            re.compile(r'https?://[^\s<>"\']+'),
        ],
        "ips": [
            # IPv4
            re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
            # IPv6 (require at least two colon-separated hex groups)
            re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b'),
        ],
        "usernames": [
            # @mentions
            re.compile(r'@[a-zA-Z0-9_]{1,30}'),
            # GitHub-style mentions
            re.compile(r'github\.com/([a-zA-Z0-9_-]+)'),
            re.compile(r'twitter\.com/([a-zA-Z0-9_]+)'),
        ],
    }
    
    def __init__(
        self,
        model_path: Path | str | None = None,
        base_model: str = "en_core_web_sm",
    ):
        """Initialize the NER extractor.
        
        Args:
            model_path: Path to custom SpaCy model (optional)
            base_model: Base SpaCy model to use if no custom model
        """
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.base_model = base_model
        
        # Load SpaCy model
        if self.model_path and self.model_path.exists():
            self.nlp = spacy.load(str(self.model_path))
        else:
            try:
                self.nlp = spacy.load(base_model)
            except OSError:
                # Model not installed, download it
                from spacy.cli import download
                download(base_model)
                self.nlp = spacy.load(base_model)
        
        # Add custom entity ruler for CTF entities
        self._add_ctf_patterns()
    
    def _add_ctf_patterns(self) -> None:
        """Add CTF-specific patterns to the NER pipeline."""
        # Add entity ruler if not already present
        if "entity_ruler" not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            
            # Add patterns for CTF entities
            patterns = [
                {"label": "FLAG", "pattern": [{"TEXT": {"REGEX": r"(flag|ctf)\{[^}]+\}"}}]},
                {"label": "HASH", "pattern": [{"TEXT": {"REGEX": r"[a-f0-9]{32,64}"}}]},
            ]
            ruler.add_patterns(patterns)
    
    def extract(self, text: str) -> ExtractedEntities:
        """Extract all entity types from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            ExtractedEntities object with all found entities
        """
        entities = ExtractedEntities()
        
        # Regex-based extraction
        entities.flags = self._extract_flags(text)
        entities.hashes = self._extract_hashes(text)
        entities.emails = self._extract_by_pattern(text, "emails")
        entities.urls = self._extract_by_pattern(text, "urls")
        entities.ips = self._extract_by_pattern(text, "ips")
        entities.usernames = self._extract_usernames(text)
        
        # SpaCy-based extraction
        doc = self.nlp(text)
        
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                entities.locations.append(ent.text)
            elif ent.label_ == "ORG":
                entities.projects.append(ent.text)
            elif ent.label_ == "PERSON":
                # Could be a username
                if ent.text not in entities.usernames:
                    entities.usernames.append(ent.text)
        
        # Deduplicate all lists
        entities.flags = list(set(entities.flags))
        entities.hashes = list(set(entities.hashes))
        entities.emails = list(set(entities.emails))
        entities.urls = list(set(entities.urls))
        entities.ips = list(set(entities.ips))
        entities.usernames = list(set(entities.usernames))
        entities.locations = list(set(entities.locations))
        entities.projects = list(set(entities.projects))
        
        return entities
    
    def _extract_by_pattern(self, text: str, pattern_type: str) -> list[str]:
        """Extract entities using regex patterns.
        
        Args:
            text: Text to search
            pattern_type: Key in PATTERNS dict
            
        Returns:
            List of matched strings
        """
        matches: list[str] = []
        
        for pattern in self.PATTERNS.get(pattern_type, []):
            for match in pattern.finditer(text):
                if match.groups():
                    matches.append(match.group(1))
                else:
                    matches.append(match.group(0))
        
        return matches
    
    def _extract_flags(self, text: str) -> list[str]:
        """Extract CTF flags from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of found flags
        """
        flags: list[str] = []
        
        for pattern in self.PATTERNS["flags"]:
            for match in pattern.finditer(text):
                flag = match.group(0)
                
                # Validate flag format
                if self._is_valid_flag(flag):
                    flags.append(flag)
        
        return flags
    
    def _is_valid_flag(self, text: str) -> bool:
        """Check if text looks like a valid CTF flag.
        
        Args:
            text: Potential flag string
            
        Returns:
            True if it looks like a flag
        """
        # Must have curly braces or look like encoded data
        if "{" in text and "}" in text:
            return True
        
        # Check for base64-like patterns
        if len(text) >= 20 and text.replace("=", "").replace("+", "").replace("/", "").isalnum():
            return True
        
        return False
    
    def _extract_hashes(self, text: str) -> list[str]:
        """Extract cryptographic hashes from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of found hashes
        """
        hashes: list[str] = []
        
        for pattern in self.PATTERNS["hashes"]:
            for match in pattern.finditer(text):
                hash_str = match.group(0).lower()
                
                # Validate it's not just a UUID or similar
                if self._is_valid_hash(hash_str):
                    hashes.append(hash_str)
        
        return hashes
    
    def _is_valid_hash(self, text: str) -> bool:
        """Check if text is a valid cryptographic hash.
        
        Args:
            text: Potential hash string
            
        Returns:
            True if it looks like a hash
        """
        # Must be hex and standard length
        valid_lengths = {32, 40, 64}  # MD5, SHA1, SHA256
        return len(text) in valid_lengths and all(c in "0123456789abcdef" for c in text)
    
    def _extract_usernames(self, text: str) -> list[str]:
        """Extract usernames and handles from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of found usernames
        """
        usernames: list[str] = []
        
        for pattern in self.PATTERNS["usernames"]:
            for match in pattern.finditer(text):
                if match.groups():
                    usernames.append(match.group(1))
                else:
                    username = match.group(0)
                    # Remove @ prefix
                    if username.startswith("@"):
                        username = username[1:]
                    usernames.append(username)
        
        return usernames
    
    def find_flags(self, text: str) -> list[str]:
        """Convenience method to find only flags.
        
        Args:
            text: Text to search
            
        Returns:
            List of found flags
        """
        return self._extract_flags(text)
    
    def save_model(self, output_path: Path | str) -> None:
        """Save the current SpaCy model.
        
        Args:
            output_path: Directory to save model to
        """
        output_path = Path(output_path).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)
        self.nlp.to_disk(output_path)
    
    def add_training_data(
        self,
        text: str,
        entities: list[tuple[int, int, str]],
    ) -> None:
        """Add training data for model fine-tuning.
        
        Args:
            text: Training text
            entities: List of (start, end, label) tuples
            
        Note:
            This is a placeholder for future fine-tuning support.
            Full fine-tuning requires collecting substantial training
            data and running spacy train.
        """
        # Future: Implement training data collection
        pass
