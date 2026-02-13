public with sharing class SalesAIOrchestrator {
    
    // The Cloud Run Endpoint for the Swarm/Platform
    private static final String SWARM_ENDPOINT = 'https://movement-voice-demo-511662304947.us-central1.run.app/api/leads/ingest';

    @future(callout=true)
    public static void handOffToPlatform(List<Id> leadIds) {
        List<Lead> leads = [SELECT Id, FirstName, LastName, Phone, Email, Company, Status, Description FROM Lead WHERE Id IN :leadIds];
        
        for (Lead l : leads) {
            try {
                processSingleLead(l);
            } catch (Exception e) {
                System.debug('Error handing off lead ' + l.Id + ': ' + e.getMessage());
            }
        }
    }

    private static void processSingleLead(Lead l) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(SWARM_ENDPOINT);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        
        // Payload aligned with Platform LeadModel
        Map<String, Object> payload = new Map<String, Object>{
            'id' => l.Id,
            'name' => l.FirstName + ' ' + l.LastName,
            'email' => l.Email,
            'phone' => l.Phone,
            'company' => l.Company,
            'status' => l.Status,
            'notes' => l.Description,
            'source' => 'salesforce_trigger'
        };
        
        req.setBody(JSON.serialize(payload));
        
        Http http = new Http();
        HttpResponse res = http.send(req);
        
        if (res.getStatusCode() != 200) {
            System.debug('Platform rejected handoff: ' + res.getBody());
        }
    }
}
