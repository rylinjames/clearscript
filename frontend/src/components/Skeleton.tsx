"use client";

export function SkeletonLine({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-gray-200 rounded-lg" />
        <div className="flex-1">
          <div className="h-3 bg-gray-200 rounded w-24 mb-2" />
          <div className="h-5 bg-gray-200 rounded w-16" />
        </div>
      </div>
      <div className="h-2 bg-gray-100 rounded w-32" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-pulse">
      <div className="border-b border-gray-100 px-6 py-4 flex gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-3 bg-gray-200 rounded w-24" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-6 py-4 border-b border-gray-50 flex gap-6">
          {[1, 2, 3, 4].map((j) => (
            <div key={j} className="h-3 bg-gray-100 rounded w-20" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-32 mb-6" />
      <div className="flex items-end gap-2 h-48">
        {[40, 65, 45, 80, 55, 70, 35, 60, 75, 50].map((h, i) => (
          <div
            key={i}
            className="flex-1 bg-gray-100 rounded-t"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function SkeletonPage() {
  return (
    <div>
      <div className="mb-8 animate-pulse">
        <div className="h-7 bg-gray-200 rounded w-64 mb-2" />
        <div className="h-4 bg-gray-100 rounded w-96" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <SkeletonChart />
    </div>
  );
}
