from dataclasses import dataclass, field

@dataclass
class SyncResult:
    created: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    skipped: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.updated) + len(self.skipped)