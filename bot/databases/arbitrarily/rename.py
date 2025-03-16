from _executer import execute

execute(
    """
        ALTER TABLE guilds
        RENAME COLUMN command_permissions TO disabled_commands;
    """
)
