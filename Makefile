.PHONY: build push deploy up test

build:
	docker build -t design-file-manager app/

push:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO)
	docker tag design-file-manager $(ECR_REPO):$(IMAGE_TAG)
	docker push $(ECR_REPO):$(IMAGE_TAG)

deploy:
	cd infra && terraform apply -auto-approve

up: build push deploy

test:
	cd app && pip install -r requirements.txt && pytest ../tests -v
