import pytest
from backend.services.voice.intent import (
    parse_spoken_currency_or_number,
    parse_duration_months,
    parse_confirmation_intent,
    parse_categorical_slot
)

def test_currency_parsing():
    assert parse_spoken_currency_or_number("4.5 lakh") == 450000.0
    assert parse_spoken_currency_or_number("4 lakh") == 400000.0
    assert parse_spoken_currency_or_number("45 thousand") == 45000.0
    assert parse_spoken_currency_or_number("50k") == 50000.0
    assert parse_spoken_currency_or_number("1.2 crore") == 12000000.0
    assert parse_spoken_currency_or_number("forty five thousand") == 45000.0
    assert parse_spoken_currency_or_number("zero") == 0.0
    assert parse_spoken_currency_or_number("no") == 0.0
    assert parse_spoken_currency_or_number("nil") == 0.0

def test_duration_parsing():
    assert parse_duration_months("3 years") == 36
    assert parse_duration_months("1.5 years") == 18
    assert parse_duration_months("24 months") == 24
    assert parse_duration_months("6 months") == 6
    assert parse_duration_months("5") == 60  # <=7 assumed years

def test_confirmation_intent():
    assert parse_confirmation_intent("yes, that is correct") is True
    assert parse_confirmation_intent("yeah right") is True
    assert parse_confirmation_intent("ha") is True
    assert parse_confirmation_intent("no, that is wrong") is False
    assert parse_confirmation_intent("nope change it") is False

def test_categorical_slot_parsing():
    assert parse_categorical_slot("employment_type", "i work in a private salaried job") == "salaried"
    assert parse_categorical_slot("employment_type", "i run a retail shop business") == "business"
    assert parse_categorical_slot("loan_purpose", "to buy a new flat home") == "home"
    assert parse_categorical_slot("loan_purpose", "higher education studies") == "education"
    assert parse_categorical_slot("residence_type", "living on rent in an apartment") == "rented"
    assert parse_categorical_slot("residence_type", "ancestral family house") == "ancestral"
