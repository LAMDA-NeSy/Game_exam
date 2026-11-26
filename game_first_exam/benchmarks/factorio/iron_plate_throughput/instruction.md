# Build an automatic iron plate factory

Use the Factorio Learning Environment to produce at least 16 iron plates automatically per 60 in-game seconds. You have one factory and up to 64 REPL actions.

Run `python /opt/fle_client.py prompt` for the game's Python API, and `python /opt/fle_client.py observe` for the current state. Each observation is JSON and includes inventory, nearby entities and game information.

Write a program using the FLE API and submit it with `python /opt/fle_client.py step 1 program.py`. Each submission runs in the same game's Python namespace. Read the native output, reward and termination flags. Use the returned `next_step` for your next submission. If a response is lost, repeat the same step number and identical source. You can look up progress with `python /opt/fle_client.py status`.

FLE checks automatic iron plate production after each action. The trial also reports the upstream Inspect production score. Stop when the factory reaches the target or the budget runs out.
