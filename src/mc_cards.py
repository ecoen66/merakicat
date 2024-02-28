CHECK_CARD = """
{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Check a Switch Configuration",
                "size": "medium",
                "weight": "bolder",
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "host",
                "label": "Hostname or IP Address"
            },
            {
                "type": "TextBlock",
                "text": "OR",
                "wrap": true,
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "file",
                "label": "File Path and Name"
            },
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Check",
                        "id": "submit_translate",
                        "style": "positive",
                        "data": "check"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "Cancel",
                        "id": "submit_cancel",
                        "style": "destructive",
                        "data": "cancel"
                    }
                ],
                "horizontalAlignment": "Center",
                "spacing": "None"
            }
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3"
    }
}
"""

OLD_TRANSLATE_CARD = """
{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Translate a Switch Config",
                "size": "medium",
                "weight": "bolder",
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "host",
                "label": "Hostname or IP Address"
            },
            {
                "type": "TextBlock",
                "text": "OR",
                "wrap": true,
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "file",
                "label": "File Path and Name"
            },
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Translate",
                        "id": "submit_translate",
                        "style": "positive",
                        "data": "translate"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "Cancel",
                        "id": "submit_cancel",
                        "style": "destructive",
                        "data": "cancel"
                    }
                ],
                "horizontalAlignment": "Center",
                "spacing": "None"
            }
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3"
    }
}
"""

TRANSLATE_CARD = """
{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Translate a Switch Config",
                "size": "Medium",
                "weight": "Bolder",
                "horizontalAlignment": "Center"
            },
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "Input.Text",
                        "placeholder": "Host",
                        "id": "host",
                        "label": "Hostname or IP Address"
                    },
                    {
                        "type": "TextBlock",
                        "text": "OR",
                        "wrap": true,
                        "horizontalAlignment": "Center"
                    },
                    {
                        "type": "Input.Text",
                        "placeholder": "Filespec",
                        "id": "file",
                        "label": "File Path and Name"
                    }
                ]
            },
            {
                "type": "TextBlock",
                "text": "AND",
                "wrap": true,
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Meraki Serial Numbers",
                "id": "sw_list",
                "label": "Comma delimited list of Meraki serial numbers"
            },
            {
                "type": "ActionSet",
                "horizontalAlignment": "Center",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Translate",
                        "id": "submit_translate",
                        "style": "positive",
                        "data": "translate"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "Cancel",
                        "id": "submit_cancel",
                        "style": "destructive",
                        "data": "cancel"
                    }
                ]
            }
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3"
    }
}
"""

MIGRATE_CARD = """
{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Migrate a switch stack to Meraki switches",
                "size": "medium",
                "weight": "bolder",
                "horizontalAlignment": "Center"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "host",
                "label": "Hostname or IP Address"
            },
            {
                "type": "Input.Text",
                "placeholder": "Placeholder text",
                "id": "network",
                "label": "Meraki network name"
            },
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Convert",
                        "id": "submit_translate",
                        "style": "positive",
                        "data": "check"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "Cancel",
                        "id": "submit_cancel",
                        "style": "destructive",
                        "data": "cancel"
                    }
                ],
                "horizontalAlignment": "Center",
                "spacing": "None"
            }
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3"
    }
}
"""


