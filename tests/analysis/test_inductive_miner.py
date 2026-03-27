from datetime import datetime, timedelta

import pandas as pd
import pytest

from analysis.discovery import (
    inductive_miner,
    ProcessTree,
    ProcessTreeOperator,
    seq_log_split,
)
from instrumentation import InMemoryBackend
from strobe import EventLog


def test_seq_log_split():
    df = pd.DataFrame(
        data={
            EventLog.CASE_ID: ["1", "2", "1", "1", "2", "2", "1", "2"],
            EventLog.ACTIVITY: ["a", "a", "b", "c", "b", "d", "a", "a"],
        }
    )
    cuts = [{"a", "b"}, {"c", "d"}]
    sublogs = seq_log_split(df, cuts)
    assert len(sublogs) == 2
    assert set(sublogs[0][EventLog.ACTIVITY].unique()) == {"a", "b"}
    assert len(sublogs[0]) == 4
    assert set(sublogs[1][EventLog.ACTIVITY].unique()) == {"c", "d"}
    assert len(sublogs[1]) == 2


@pytest.mark.asyncio
async def test_inductive_miner_xorg():
    a, b, c = "A", "B", "C"
    L = [
        (a, b),
        (a, c),
    ]

    el = EventLog(backend=InMemoryBackend())

    timestamp = datetime.now()

    for trace_id, trace in enumerate(L):
        for act in trace:
            timestamp += timedelta(seconds=1)
            await el.add_event(case_id=str(trace_id), activity=act, timestamp=timestamp)

    df = await el.to_dataframe()

    model = inductive_miner(df)

    assert model is not None

    expected_model = ProcessTree(
        operator=ProcessTreeOperator.SEQ,
        subtrees=[
            ProcessTree(activity=a),
            ProcessTree(
                operator=ProcessTreeOperator.XOR,
                subtrees=[
                    ProcessTree(activity=b),
                    ProcessTree(activity=c),
                ],
            ),
        ],
    )

    assert str(model) == str(expected_model)


@pytest.mark.asyncio
async def test_inductive_miner_discovery():
    a, b, c, d, e, f, g, h = "A", "B", "C", "D", "E", "F", "G", "H"
    L = [
        {a, c, d, e, h},
        {a, b, d, e, g},
        {a, d, c, e, h},
        {a, b, d, e, h},
        {a, c, d, e, g},
        {a, d, c, e, g},
        {a, b, d, e, h},
        {a, c, d, e, f, d, b, e, h},
        {a, d, b, e, g},
        {a, c, d, e, f, b, d, e, h},
        {a, c, d, e, f, b, d, e, g},
        {a, c, d, e, f, d, b, e, g},
        {a, d, c, e, f, c, d, e, h},
        {a, d, c, e, f, d, b, e, h},
        {a, d, c, e, f, b, d, e, g},
        {a, c, d, e, f, b, d, e, f, d, b, e, g},
        {a, d, c, e, f, d, b, e, g},
        {a, d, c, e, f, b, d, e, f, b, d, e, g},
        {a, d, c, e, f, d, b, e, f, b, d, e, h},
        {a, d, b, e, f, b, d, e, f, d, b, e, g},
        {a, d, c, e, f, d, b, e, f, c, d, e, f, d, b, e, g},
    ]

    el = EventLog(backend=InMemoryBackend())

    timestamp = datetime.now()

    for trace_id, trace in enumerate(L):
        for act in trace:
            timestamp += timedelta(seconds=1)
            await el.add_event(case_id=str(trace_id), activity=act, timestamp=timestamp)

    df = await el.to_dataframe()
    model = inductive_miner(df)

    assert model is not None

    # M' = ->(a, loop(->(^(x(b,c),d),e),f),x(h,g))
    expected_model = ProcessTree(
        operator=ProcessTreeOperator.SEQ,
        subtrees=[
            ProcessTree(activity=a),
            ProcessTree(
                operator=ProcessTreeOperator.LOOP,
                subtrees=[
                    ProcessTree(
                        operator=ProcessTreeOperator.SEQ,
                        subtrees=[
                            ProcessTree(
                                operator=ProcessTreeOperator.PARALLEL,
                                subtrees=[
                                    ProcessTree(
                                        operator=ProcessTreeOperator.XOR,
                                        subtrees=[
                                            ProcessTree(activity=b),
                                            ProcessTree(activity=c),
                                        ],
                                    ),
                                    ProcessTree(activity=d),
                                ],
                            ),
                            ProcessTree(activity=e),
                        ],
                    ),
                    ProcessTree(activity=f),
                ],
            ),
            ProcessTree(
                operator=ProcessTreeOperator.XOR,
                subtrees=[ProcessTree(activity=h), ProcessTree(activity=g)],
            ),
        ],
    )

    assert str(model) == str(expected_model)
