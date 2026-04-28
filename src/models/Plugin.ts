import { Schema, model, Document } from 'mongoose';

export interface IPlugin extends Document {
  name: string;
  description: string;
  version: string;
  isActive: boolean;
  settings: Record<string, unknown>;
  handler: string;
  addedAt: Date;
}

const pluginSchema = new Schema<IPlugin>({
  name: { type: String, required: true, unique: true },
  description: { type: String, default: '' },
  version: { type: String, default: '1.0.0' },
  isActive: { type: Boolean, default: false },
  settings: { type: Schema.Types.Mixed, default: {} },
  handler: { type: String, default: '' },
  addedAt: { type: Date, default: Date.now },
});

export const Plugin = model<IPlugin>('Plugin', pluginSchema);
