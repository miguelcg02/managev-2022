import seaborn as sns
from heatmap import corrplot
from matplotlib import pyplot as plt


def plot_exploratory_analysis(segments):
    # Correlation with consumption
    print(segments.corr()["consumption"].sort_values())

    heat_cols = [
        "mean_acc",
        "slope",
        "mean_power",
        "mean_current",
        "speed",
        "mean_soc",
        "consumption_per_km",
    ]

    segments_copy = segments.copy()
    segments_copy = segments_copy.rename(columns={"mean_speed": "speed"})
    corr = segments_copy[heat_cols].corr()
    plt.figure(figsize=(8, 8))
    corrplot(corr.sort_values(["slope"]), size_scale=500)
    plt.show()

    plt.scatter(x=segments.consumption, y=segments.slope)
    plt.show()

    sns.pairplot(
        segments_copy.dropna().sort_values(["slope"]),
        hue="slope_cat",
        palette="mako",
        vars=[
            "min_acc",
            "slope",
            "mean_power",
            "speed",
            "consumption_per_km",
        ],
        kind="scatter",
        # height=8,
    )
    plt.show()
