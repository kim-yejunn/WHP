import os
import numpy as np
import torch
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision.models.feature_extraction import create_feature_extractor
from torchvision import datasets, transforms
from PIL import Image
from numpy import dot
from numpy.linalg import norm
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, storage
import urllib.request

# Firebase 초기화
cred = credentials.Certificate('/Users/dust/Downloads/WEB Firebase(06.10)/webhotplace-1cce1-firebase-adminsdk-bfvwa-07f658a26f.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'webhotplace-1cce1.appspot.com'
})

bucket = storage.bucket()

# 1. EfficientNet-B0 모델 설정
weights = EfficientNet_B0_Weights.DEFAULT
model = efficientnet_b0(weights=weights)
model = create_feature_extractor(model, return_nodes={'avgpool': 'avgpool'})
model.eval()

# 2. 이미지 전처리 함수
preprocess = transforms.Compose([
    transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.CenterCrop(224),
    transforms.ToTensor()
])

# 3. 데이터셋 로드 및 전처리
def download_images_from_firebase():
    all_image_paths = []
    blobs = bucket.list_blobs()
    for blob in blobs:
        if blob.name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            local_path = os.path.join('images_database', blob.name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
            all_image_paths.append(local_path)
    return all_image_paths

all_image_paths = download_images_from_firebase()

# 4. 이미지 특징 추출 함수
def extract_features(image_paths):
    features = []
    paths = []
    with torch.no_grad():
        for image_path in image_paths:
            image = Image.open(image_path).convert('RGB')
            image = preprocess(image).unsqueeze(0)
            output = model(image)
            features.append(output['avgpool'].flatten().numpy())
            paths.append(image_path)
    return np.array(features), paths

# 5. 데이터셋 이미지 특징 벡터 추출 및 저장
dataset_features, image_paths = extract_features(all_image_paths)

# 6. 코사인 유사도 계산 함수
def cos_sim(A, B):
    return dot(A, B) / (norm(A) * norm(B))

# 7. 입력 이미지 처리 및 특징 벡터 추출 함수
def predict(image_path):
    image = Image.open(image_path).convert('RGB')
    image = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        output = model(image)
        image_feature = output['avgpool'].flatten().numpy()
    return image_feature

# 8. 가장 유사한 이미지 찾기 함수
def find_most_similar_image(input_image_path):
    input_feature = predict(input_image_path)
    similarities = [cos_sim(input_feature, feature) for feature in dataset_features]
    most_similar_idx = np.argmax(similarities)
    most_similar_image_path = image_paths[most_similar_idx]
    return most_similar_image_path

# 9. 이미지 시각화 함수
def display_images(input_image_path, most_similar_image_path):
    input_image = Image.open(input_image_path).convert('RGB')
    similar_image = Image.open(most_similar_image_path).convert('RGB')

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(input_image)
    axes[0].set_title('Input Image')
    axes[0].axis('off')

    axes[1].imshow(similar_image)
    axes[1].set_title('Most Similar Image')
    axes[1].axis('off')

    plt.show()

# 테스트용 입력 이미지 경로
input_image_path = 'webhotplace-1cce1.appspot.com/test.jpg'  # 입력 이미지 경로 설정

# 가장 유사한 이미지 찾기 및 출력
most_similar_image = find_most_similar_image(input_image_path)
print(f"Input image: {input_image_path}")
print(f"Most similar image: {most_similar_image}")

# 입력 이미지와 가장 유사한 이미지 시각화
display_images(input_image_path, most_similar_image)