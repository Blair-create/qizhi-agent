import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold">页面不存在</h1>
      <p className="text-gray-500">地址可能有误，或页面已被移除。</p>
      <Link className="text-blue-600 hover:underline" href="/chat">返回对话</Link>
    </main>
  );
}
