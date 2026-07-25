export type ApplicationStatus =
  | 'new'
  | 'tailored'
  | 'applied'
  | 'replied'
  | 'interview'
  | 'rejected'
  | 'offer'
  | 'archived';

export interface JobApplication {
  id: string;
  title: string;
  company: string;
  url: string;
  jdText: string;
  status: ApplicationStatus;
  resume?: unknown;
  matchResult?: unknown;
  tailoredResume?: unknown;
  pdfBase64?: string;
  createdAt: string;
  /** Last time the user got real new signal on this application (reply, status change, note). */
  lastSignalAt: string;
  /** Free-form triage notes, most recent first. */
  notes: { at: string; text: string }[];
}
