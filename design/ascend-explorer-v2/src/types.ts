// V2 design contract: types for future standalone web explainer; no runtime claims.
export type ClaimLevel =
  | "official_product" | "official_architecture" | "official_framework"
  | "upstream_case" | "derived_inference" | "local_test" | "unverified";

export type SupportStatus = "confirmed_in_version" | "unsupported_in_version" | "not_assessed";
export type DeviceForm =
  | "module" | "edge_system" | "accelerator_card" | "inference_server"
  | "training_server" | "compute_pod";
export type LifecycleStage = "request" | "queue" | "prefill" | "decode" | "stream";
export type PresentationMode =
  | "teaching_demo" | "official_source" | "author_reported"
  | "project_software_test" | "project_npu_measured";

export interface Provenance {
  sourceUrl: string;
  sourceTitle?: string;
  retrievedAt?: string;
  versionScope?: string;
  claimLevel: ClaimLevel;
  appliesTo?: string[];
  limitations: string[];
}

export interface QuantitativeSpecs {
  computeTOPS: number | null;
  deviceMemoryGB: number | null;
  memoryBandwidthGBs: number | null;
  interconnectGBs: number | null;
  powerW: number | null;
}
export interface ProductCard {
  id: string;
  name: string;
  family: string;
  form: DeviceForm;
  usage: "edge" | "inference" | "training_and_inference";
  processor: string | null;
  remark: string;
  quantitative: QuantitativeSpecs;
  compatibilityStatus: SupportStatus;
  sourceUrl: string;
  sourceVersion: string;
  claimLevel: "official_product";
  limitations: string[];
}
export interface ProcessorResearchTopic {
  id: string;
  name: string;
  level: "processor_research_topic";
  sourceStatus: "specific_product_datasheet_not_collected";
  notAPhysicalCard: true;
  notes: string;
}

export type OperatorFrameKind = "conceptual_diagram" | "evidence_or_validation";
export type OperatorFrameSlug =
  | "input" | "execution" | "memory" | "bottleneck" | "optimization" | "validation";
export interface OperatorFrame {
  index: number;
  slug: OperatorFrameSlug;
  label: string;
  kind: OperatorFrameKind;
  observed: false;
}
export interface OperatorStory {
  id: string;
  title: string;
  stages: ("prefill" | "decode")[];
  claimLevel: "derived_inference";
  sourceUrls: string[];
  frames: OperatorFrame[];
  limitations: string[];
  localPerformanceEvidence: false;
}

export interface ExhibitModule {
  id: string;
  hash: string;
  title: string;
  interaction: string;
  behavior: string;
  acceptance: string[];
  implementationStatus: "design_only" | "implemented" | "verified";
  evidenceDrawer: boolean;
  keyboard: string;
  motion: "reduced-motion-safe";
}

export interface BenchmarkEvidence {
  status: "not_measured" | "measured";
  hardwareSKU: string | null;
  cannVersion: string | null;
  frameworkSha: string | null;
  modelSha: string | null;
  profilerArtifactUrl: string | null;
  workloadId: string | null;
  ttftP50Ms: number | null;
  tpotP50Ms: number | null;
  e2eP95Ms: number | null;
  throughputTokensPerSecond: number | null;
}
export const EMPTY_BENCHMARK: BenchmarkEvidence = {
  status: "not_measured",
  hardwareSKU: null, cannVersion: null, frameworkSha: null,
  modelSha: null, profilerArtifactUrl: null, workloadId: null,
  ttftP50Ms: null, tpotP50Ms: null, e2eP95Ms: null,
  throughputTokensPerSecond: null
};

export function formatVerifiedMetric(value: number | null, unit: string): string {
  if (value === null) return "未核验";
  if (!Number.isFinite(value) || value < 0) throw new Error("Invalid metric");
  return String(value) + " " + unit;
}

export function performanceCanBeCalledMeasured(x: BenchmarkEvidence): boolean {
  return x.status === "measured"
    && [x.hardwareSKU, x.cannVersion, x.frameworkSha, x.modelSha,
        x.profilerArtifactUrl, x.workloadId].every(Boolean)
    && [x.ttftP50Ms, x.tpotP50Ms, x.e2eP95Ms,
        x.throughputTokensPerSecond].every(v => v !== null && Number.isFinite(v));
}
