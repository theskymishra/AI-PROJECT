from app.ai.knowledge.engine import KnowledgeEngine, Rule
from app.ai.knowledge.parser import Atom, parse_atom, parse_rule


def A(name, *args):
    return Atom(name, tuple(args))


def test_parser_reads_atoms_and_rules():
    assert parse_atom("Unsafe(R17)") == A("Unsafe", "R17")
    premises, conclusion = parse_rule("HighFailureProb(R) & Road(R) -> Unsafe(R)")
    assert premises == (A("HighFailureProb", "R"), A("Road", "R"))
    assert conclusion == A("Unsafe", "R")


def test_forward_chaining_reaches_fixpoint_and_records_explanation():
    kb = KnowledgeEngine(
        facts={A("HighFailureProb", "R17")},
        rules=(
            Rule("risk_to_unsafe", (A("HighFailureProb", "R"),), A("Unsafe", "R")),
            Rule("unsafe_to_avoid", (A("Unsafe", "R"),), A("Avoid", "R")),
        ),
    )
    result = kb.infer()
    assert "Unsafe(R17)" in result.derived_facts
    assert "Avoid(R17)" in result.derived_facts
    assert [step.rule_name for step in result.steps] == ["risk_to_unsafe", "unsafe_to_avoid"]
    assert result.iterations == 3


def test_conjunctive_query_returns_variable_bindings():
    kb = KnowledgeEngine(
        facts={A("Road", "R1"), A("Road", "R2"), A("Unsafe", "R2")},
    )
    result = kb.query((A("Road", "R"), A("Unsafe", "R")), execute_inference=False)
    assert result.bindings == [{"R": "R2"}]
    assert result.count == 1


def test_constants_and_variables_can_mix():
    kb = KnowledgeEngine(facts={A("Connects", "R17", "N5", "N10")})
    result = kb.query((A("Connects", "R", "N5", "N"),), execute_inference=False)
    assert result.bindings == [{"N": "N10", "R": "R17"}]
