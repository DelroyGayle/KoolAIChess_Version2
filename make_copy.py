def makecopy(original):

    # if isinstance(original, Position):
    #     return original.clone()

    if not isinstance(original, (dict, list, set)):
        return original  # i.e. immutable item

    if isinstance(original, set):
        return set(original)

    if isinstance(original, dict):
        return dict(original)

    # Handle list of lists
    # Make a deep copy of the list
    return [makecopy(i) for i in original]
