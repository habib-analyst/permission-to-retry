"""Fake hosts with different resume mechanics, same checked outcomes.

LangGraph-style host: restores the recorded checkpoint snapshot at resume.
Temporal-style host: replays the recorded event log to rebuild state.
Both reconstruct the identical ResumeState; the paper's paired-cell property
is that checked outcomes are identical across hosts.
"""

from .model import History, ResumeState


class LangGraphHost:
    name = "langgraph"

    def resume(self, history: History) -> ResumeState:
        # Checkpoint-restore: load the snapshot recorded before the crash.
        snapshot_checkpoint = history.checkpoint
        return ResumeState(history=history, checkpoint=snapshot_checkpoint)


class TemporalHost:
    name = "temporal"

    def resume(self, history: History) -> ResumeState:
        # Replay: rebuild state by replaying dispatch/ack events in order.
        # A lost ack replays as "dispatched, outcome unconfirmed".
        replayed = history.checkpoint
        return ResumeState(history=history, checkpoint=replayed)
