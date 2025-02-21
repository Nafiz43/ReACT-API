import json
import argparse
import pandas as pd

def filter_json_by_features(data, features):
    """
    Filters a list of JSON objects by checking whether any of the provided features
    are present (in the 'Features' key as a comma-separated string).
    """
    filtered_data = []
    for entry in data:
        entry_features = set(map(str.strip, entry.get("Features", "").split(",")))
        if any(feature in entry_features for feature in features):
            filtered_data.append(entry)
    return filtered_data

def calculate_feature_differences(df, month_n, feature_list):
    """
    For each feature, calculates the difference between the sum of values for months
    in the window [month_n-2, month_n] and the overall average.
    Returns a list of features where this difference is less than or equal to zero.
    """
    avg_feature_values = {}
    for feature in feature_list:
        avg_feature_values[feature] = df[feature].mean()

    monthly_feature_values = {}
    for feature in feature_list:
        # Filter the dataframe for the relevant months (n-2 to n)
        monthly_values = df[(df['month'] >= month_n-2) & (df['month'] <= month_n)][feature]
        monthly_feature_values[feature] = monthly_values.sum()

    differences = {}
    for feature in feature_list:
        differences[feature] = monthly_feature_values[feature] - avg_feature_values[feature]

    negative_or_zero_features = [feature for feature, diff in differences.items() if diff <= 0]
    return negative_or_zero_features

def ReACT_Extractor(original_data, feature_data: pd.DataFrame, month_n: int, write_output: bool = True) -> dict:
    """
    Generates a child JSON by:
      1. Calculating which features (from a predefined list) have non-positive differences.
      2. Filtering the parent JSON (original_data) for entries that include any of those features.
      3. Sorting the filtered JSON by the 'Importance' key in descending order.
      4. Optionally writing the resulting JSON to `extracted_react.json` if write_output=True.

    Returns the sorted JSON data.
    """
    feature_list = [
        's_avg_clustering_coef',
        't_num_dev_nodes',
        't_num_dev_per_file',
        't_graph_density',
        'st_num_dev',
        't_net_overlap'
    ]
    processed_features = calculate_feature_differences(feature_data, month_n, feature_list)
    filtered_json = filter_json_by_features(original_data, processed_features)
    sorted_json = sorted(filtered_json, key=lambda x: x.get("Importance", 0), reverse=True)

    if write_output:
        with open("output/extracted_react.json", 'w') as json_file:
            json.dump(sorted_json, json_file, indent=4)
        print("ReACTs saved in `extracted_react.json` file.")

    return sorted_json

def main():
    parser = argparse.ArgumentParser(
        description="ReACT Extractor: Generate a child JSON from a parent JSON and a CSV file."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the CSV file from net-caches (generated by pex-forecaster)."
    )
    parser.add_argument(
        "--month",
        type=int,
        default=9,
        help="The month number to use for the extraction (default: 9)."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate output for all months in a single JSON file."
    )
    args = parser.parse_args()

    parent_json = "react_extractor/react_set.json"
    # Load the parent JSON file.
    with open(parent_json, 'r') as json_file:
        original_data = json.load(json_file)

    # Load the CSV file as a DataFrame.
    feature_data = pd.read_csv(args.csv)

    if args.all:
        # Generate combined results for ALL months found in the CSV
        all_months = sorted(feature_data['month'].unique())
        all_results = {}

        for m in all_months:
            # Cast m to int to avoid JSON key issues with numpy.int64
            result_for_month = ReACT_Extractor(
                original_data,
                feature_data,
                month_n=int(m),  # <-- cast here
                write_output=False
            )
            all_results[int(m)] = result_for_month  # also safe for dict keys

        # Write the final dictionary with all months to a single JSON file
        with open("output/extracted_react.json", 'w') as out_file:
            json.dump(all_results, out_file, indent=4)
        print("ReACTs for ALL months saved in `extracted_react.json` file.")
    else:
        # Single-month logic (original default)
        reacts = ReACT_Extractor(original_data, feature_data, args.month)
        # For demonstration purposes, print the extracted JSON.
        print(json.dumps(reacts, indent=4))

if __name__ == "__main__":
    main()
