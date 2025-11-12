import kagglehub

# Download latest version
path = kagglehub.dataset_download("jaderz/hospital-beds-management")

print("Path to dataset files:", path)
