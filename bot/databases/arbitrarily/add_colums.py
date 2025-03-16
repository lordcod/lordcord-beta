from _executer import execute


execute(
    """
        ALTER TABLE guilds
        ADD 
        ideas JSON DEFAULT '{}'; 
    """
)
