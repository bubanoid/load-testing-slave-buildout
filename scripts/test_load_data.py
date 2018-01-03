# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from uuid import uuid4

now = datetime.now()

test_tender_data = {
    "title": u"футляри до державних нагород",
    "title_en": u"Cases for state awards",
    "procuringEntity": {
        "kind": 'general',
        "name": u"Державне управління справами",
        "name_en": u"State administration",
        "identifier": {
            "legalName_en": u"dus.gov.ua",
            "scheme": u"UA-EDR",
            "id": u"00037256",
            "uri": u"http://www.dus.gov.ua/"
        },
        "address": {
            "countryName": u"Україна",
            "postalCode": u"01220",
            "region": u"м. Київ",
            "locality": u"м. Київ",
            "streetAddress": u"вул. Банкова, 11, корпус 1"
        },
        "contactPoint": {
            "name": u"Державне управління справами",
            "name_en": u"State administration",
            "telephone": u"0440000000"
        },
    },
    "value": {
        "amount": 500,
        "currency": u"UAH"
    },
    "minimalStep": {
        "amount": 35,
        "currency": u"UAH"
    },
    "items": [
        {
            "description": u"футляри до державних нагород",
            "description_en": u"Cases for state awards",
            "classification": {
                "scheme": u"ДК021",
                "id": u"44617100-9",
                "description": u"Cartons"
            },
            "additionalClassifications": [
                {
                    "scheme": u"ДКПП",
                    "id": u"17.21.1",
                    "description": u"папір і картон гофровані, паперова й картонна тара"
                }
            ],
            "unit": {
                "name": u"item",
                "code": u"44617100-9"
            },
            "quantity": 5,
            "deliveryDate": {
                 "startDate": (now + timedelta(days=20)).isoformat(),
                 "endDate": (now + timedelta(days=500)).isoformat()
             },
            "deliveryAddress": {
                "countryName": u"Україна",
                "postalCode": "79000",
                "region": u"м. Київ",
                "locality": u"м. Київ",
                "streetAddress": u"вул. Банкова 1"
            }
        }
    ],
    "tenderPeriod": {
        "endDate": (now + timedelta(days=40)).isoformat()
    },
    "procurementMethodType": "aboveThresholdEU",
}

test_tender_data_with_lots = {
    "title": u"футляри до державних нагород",
    "title_en": u"Cases for state awards",
    "procuringEntity": {
        "kind": 'general',
        "name": u"Державне управління справами",
        "name_en": u"State administration",
        "identifier": {
            "legalName_en": u"dus.gov.ua",
            "scheme": u"UA-EDR",
            "id": u"00037256",
            "uri": u"http://www.dus.gov.ua/"
        },
        "address": {
            "countryName": u"Україна",
            "postalCode": u"01220",
            "region": u"м. Київ",
            "locality": u"м. Київ",
            "streetAddress": u"вул. Банкова, 11, корпус 1"
        },
        "contactPoint": {
            "name": u"Державне управління справами",
            "name_en": u"State administration",
            "telephone": u"0440000000"
        },
    },
    "value": {
        "amount": 500,
        "currency": u"UAH"
    },
    "minimalStep": {
        "amount": 35,
        "currency": u"UAH"
    },
    "items": [
        {
            "description": u"футляри до державних нагород",
            "description_en": u"Cases for state awards",
            "classification": {
                "scheme": u"ДК021",
                "id": u"44617100-9",
                "description": u"Cartons"
            },
            "additionalClassifications": [
                {
                    "scheme": u"ДКПП",
                    "id": u"17.21.1",
                    "description": u"папір і картон гофровані, паперова й картонна тара"
                }
            ],
            "unit": {
                "name": u"item",
                "code": u"44617100-9"
            },
            "quantity": 5,
            "deliveryDate": {
                 "startDate": (now + timedelta(days=20)).isoformat(),
                 "endDate": (now + timedelta(days=500)).isoformat()
             },
            "deliveryAddress": {
                "countryName": u"Україна",
                "postalCode": "79000",
                "region": u"м. Київ",
                "locality": u"м. Київ",
                "streetAddress": u"вул. Банкова 1"
            }
        }
    ],
    "tenderPeriod": {
        "endDate": (now + timedelta(days=40)).isoformat()
    },
    "procurementMethodType": "aboveThresholdEU",
    "lots": [
        {   'id': uuid4().hex,
            'title': 'lot title',
            'description': 'lot description',
            'value': test_tender_data['value'],
            'minimalStep': test_tender_data['minimalStep'],
        },
        {
            'id': uuid4().hex,
            'title': 'lot title',
            'description': 'lot description',
            'value': test_tender_data['value'],
            'minimalStep': test_tender_data['minimalStep'],
        }
        ]
}

test_bid = {
        "tenderers": [ {
            "name": u"Державне управління справами",
            "name_en": u"State administration",
            "identifier": {
                "legalName_en": u"dus.gov.ua",
                "scheme": u"UA-EDR",
                "id": u"00037256",
                "uri": u"http://www.dus.gov.ua/"
            },
            "address": {
                "countryName": u"Україна",
                "postalCode": u"01220",
                "region": u"м. Київ",
                "locality": u"м. Київ",
                "streetAddress": u"вул. Банкова, 11, корпус 1"
            },
            "contactPoint": {
                "name": u"Державне управління справами",
                "name_en": u"State administration",
                "telephone": u"0440000000"
            }
        }],
        "lotValues": [],
        'status': 'draft',
        'selfQualified': True,
        'selfEligible': True
    }

test_lots = [
    {
        'title': 'lot title',
        'description': 'lot description',
        'value': test_tender_data['value'],
        'minimalStep': test_tender_data['minimalStep'],
    }
]

test_value = {
            "amount": 479,
            "currency": "UAH",
            "valueAddedTaxIncluded": True
        }
