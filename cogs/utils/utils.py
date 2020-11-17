def human_join(args):
    if len(args) == 1:
        return args[0]
    return ', '.join(args[:-1]) + f' and {args[-1]}'
