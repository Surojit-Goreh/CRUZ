export interface Provider {
  id: string;
  name: string;
  tier_label: string;
  description: string;
  tags: string[];
  docs_url: string;
  get_key_url: string;
  default_model: string;
  available_models: string[];
  selected_model: string;
  requires_account_id: boolean;
  account_id_label?: string;
  account_id?: string;
  how_to_create_guide: string[];
  icon_type: string;
  has_key: boolean;
  masked_key: string;
  connected: boolean;
  last_tested_at?: string;
  error_message?: string;
}
