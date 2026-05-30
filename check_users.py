import sys; sys.path.insert(0, '.')
from core.config_loader import config
config.load()
from auth.user_registry import registry
registry.init_db()
users = registry.get_all()
print(f"Total enrolled users: {len(users)}")
for u in users:
    print(f"  ID={u['id']}  Name={u['name']}  Authorized={u['authorized']}  Shape={u['embedding'].shape}")
if not users:
    print("  (none — registry is empty)")
