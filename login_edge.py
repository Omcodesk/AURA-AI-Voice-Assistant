from core.result_types import ParsedCommand
from actions.whatsapp import handle_open_whatsapp

print("Booting Edge WebDriver...")
cmd = ParsedCommand(
    intent="whatsapp",
    action="open_chat",
    target="",
    arguments={},
    requires_auth=False,
    requires_confirmation=False,
    source_text="open whatsapp"
)

handle_open_whatsapp(cmd)
