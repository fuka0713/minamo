// 画像の保存先（SeaweedFS）。S3 と同じ使い方ができる
import { CreateBucketCommand, DeleteObjectCommand, GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const BUCKET = process.env.S3_BUCKET ?? "screenshots";

const s3 = new S3Client({
  endpoint: process.env.S3_ENDPOINT, // 例：http://storage:8333
  region: "us-east-1", // S3 互換ストレージでは何でもよい
  forcePathStyle: true,
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY ?? "app",
    secretAccessKey: process.env.S3_SECRET_KEY ?? "app",
  },
});

// 起動したときに、画像を入れるバケットを作る（もうあればそのまま）
export async function createBucket() {
  try {
    await s3.send(new CreateBucketCommand({ Bucket: BUCKET }));
  } catch (err: any) {
    if (err.name !== "BucketAlreadyOwnedByYou" && err.name !== "BucketAlreadyExists") throw err;
  }
}

export async function saveImage(key: string, data: Buffer, type: string) {
  await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: data, ContentType: type }));
}

export async function loadImage(key: string) {
  const res = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  return { data: Buffer.from(await res.Body!.transformToByteArray()), type: res.ContentType ?? "image/png" };
}

export async function removeImage(key: string) {
  await s3.send(new DeleteObjectCommand({ Bucket: BUCKET, Key: key }));
}
