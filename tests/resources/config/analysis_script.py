def analyze(df, **tools):
    return df.resample("6H").mean()