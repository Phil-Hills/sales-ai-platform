public with sharing class SalesAICallout {
    // TODO: Replace with Named Credential or Custom Metadata in production
    private static final String ENDPOINT = 'https://sales-ai-platform-235894147478.us-central1.run.app'; 

    public class AgentException extends Exception {}

    @AuraEnabled
    public static String chatWithAgent(String text, String thinkingLevel, String leadId) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT + '/demo');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        
        // Context payload
        Map<String, Object> payload = new Map<String, Object>{
            'text' => text,
            'thinking_level' => thinkingLevel,
            'session_id' => 'sf_' + UserInfo.getUserId(),
            'context' => new Map<String, String>{
                'lead_id' => leadId,
                'source' => 'Salesforce'
            }
        };
        
        req.setBody(JSON.serialize(payload));
        
        Http http = new Http();
        HttpResponse res = http.send(req);
        
        // Handle Paywall / Subscription Limits
        if (res.getStatusCode() == 402 || res.getStatusCode() == 403) {
             Map<String, Object> errorRes = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
             // Throw specific exception for LWC to catch
             throw new AgentException((String)errorRes.get('detail') ?? 'Subscription limit reached.');
        }
        
        if (res.getStatusCode() != 200) {
            throw new AgentException('Error connecting to AI Agent: ' + res.getStatus());
        }

        return res.getBody();
    }
    
    @AuraEnabled
    public static String getResearch(String company) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT + '/api/research');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(new Map<String, Object>{'company' => company}));
        
        try {
            HttpResponse res = new Http().send(req);
            if (res.getStatusCode() == 200) {
                return res.getBody();
            }
        } catch(Exception e) {
            throw new AgentException('Research failed: ' + e.getMessage());
        }
        return '{}';
    }
}
