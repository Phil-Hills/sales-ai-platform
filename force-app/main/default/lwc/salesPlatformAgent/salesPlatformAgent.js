import { LightningElement, api, wire, track } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import LEAD_COMPANY from '@salesforce/schema/Lead.Company';
import chatWithAgent from '@salesforce/apex/SalesAICallout.chatWithAgent';
import getResearch from '@salesforce/apex/SalesAICallout.getResearch';

export default class SalesPlatformAgent extends LightningElement {
    @api recordId;
    @track messages = [];
    @track input = '';
    @track research = null;

    @track isThinking = false;
    @track isPaywalled = false;
    @track isPremium = false; // TODO: Fetch from backend status

    @wire(getRecord, { recordId: '$recordId', fields: [LEAD_COMPANY] })
    lead;

    handleInputChange(event) {
        this.input = event.target.value;
    }

    async handleSend() {
        if (!this.input) return;

        // Optimistic UI update
        const userText = this.input;
        this.messages.push({
            id: Date.now(),
            text: userText,
            sender: 'user',
            class: 'outbound'
        });

        this.input = '';
        this.isThinking = true;

        // Scroll to bottom
        setTimeout(() => {
            const chatDiv = this.template.querySelector('.chat-window');
            if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
        }, 100);

        try {
            // Call Backend
            const res = await chatWithAgent({
                text: userText,
                thinkingLevel: 'medium',
                leadId: this.recordId
            });

            const data = JSON.parse(res);

            // Check for backend-reported paywall (if 200 OK but business logic denial)
            if (data.paywall) {
                this.isPaywalled = true;
                this.messages.push({
                    id: Date.now() + 1,
                    text: data.text,
                    sender: 'bot',
                    class: 'error'
                });
            } else {
                this.messages.push({
                    id: Date.now() + 1,
                    text: data.text,
                    sender: 'bot',
                    class: 'inbound'
                });
            }

        } catch (e) {
            console.error('Agent Error', e);
            let errorMsg = e.body ? e.body.message : e.message;

            if (errorMsg.includes('Subscription limit') || errorMsg.includes('402')) {
                this.isPaywalled = true;
            }

            this.messages.push({
                id: Date.now() + 1,
                text: 'Error: ' + errorMsg,
                sender: 'bot',
                class: 'error'
            });
        } finally {
            this.isThinking = false;
            // Scroll again
            setTimeout(() => {
                const chatDiv = this.template.querySelector('.chat-window');
                if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
            }, 100);
        }
    }

    async handleResearch() {
        const company = getFieldValue(this.lead.data, LEAD_COMPANY);
        if (!company) {
            // Fallback or alert
            this.messages.push({
                id: Date.now(),
                text: '⚠️ Company field is empty. Cannot perform research.',
                sender: 'system',
                class: 'error'
            });
            return;
        }

        this.isThinking = true;
        try {
            const res = await getResearch({ company });
            this.research = JSON.parse(res);
            this.messages.push({
                id: Date.now(),
                text: `✅ Research completed for ${company}. See summary above.`,
                sender: 'system',
                class: 'inbound'
            });
        } catch (e) {
            this.messages.push({
                id: Date.now(),
                text: 'Research Error: ' + (e.body ? e.body.message : e.message),
                sender: 'system',
                class: 'error'
            });
        } finally {
            this.isThinking = false;
        }
    }

    handleUpgradeClick() {
        // In a real app, this would open a URL or flow
        window.open('https://movement-voice-demo-511662304947.us-central1.run.app/admin', '_blank');
    }
}
