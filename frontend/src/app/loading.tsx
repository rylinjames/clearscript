import { SkeletonCard } from "@/components/Skeleton";

export default function Loading() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-48 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-80 mb-8" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div className="h-64 bg-gray-200 rounded-xl" />
    </div>
  );
}
