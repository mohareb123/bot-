import { Schema, model, Document } from 'mongoose';

export interface ILog extends Document {
  userId: number;
  action: string;
  details: string;
  chatId: number;
  timestamp: Date;
  success: boolean;
  duration: number;
}

const logSchema = new Schema<ILog>({
  userId: { type: Number, required: true, index: true },
  action: { type: String, required: true, index: true },
  details: { type: String, default: '' },
  chatId: { type: Number, default: 0 },
  timestamp: { type: Date, default: Date.now, index: true },
  success: { type: Boolean, default: true },
  duration: { type: Number, default: 0 },
});

logSchema.index({ timestamp: -1 });
logSchema.index({ userId: 1, timestamp: -1 });

export const Log = model<ILog>('Log', logSchema);
