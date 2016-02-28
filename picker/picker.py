import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2
import json
import random

admin_white_list=["test@example.com",
                  "feeley19@gmail.com",
                  "matt@phntms.com",
                  "josua@phntms.com",
                  "lydia@phntms.com",
                  "rx@phntms.com",]

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)




def getAllPhantoms():
    """
    Get all phantom entities, if none exist, 
    load them in from ghosts.json 
    """

    phantoms = Phantom.query().fetch()
    if len(phantoms)==0:
        data=[]
        with open('ghosts.json') as data_file:    
            data = json.load(data_file)
        for d in data:

            p=Phantom(name=d["Ghost name"],description=d["Description"])

            p.put()
        phantoms = Phantom.query().fetch()
    return phantoms


class Phantom(ndb.Model):
    """Model for each ghost entry"""
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    def toDict(self):
        return {"name":self.name,"description":self.description}



class Person(ndb.Model):
    """Model For each berson"""
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    creator = ndb.StringProperty()

    phantom_name=ndb.StructuredProperty(Phantom)



class MainPage(webapp2.RequestHandler):
    """
    Main index page that displays:

    1. Greeting
    2. Pick your name link
    3. List of taken phantom nicknames
    4. List of phantoms with no person assigned

    """

    def get(self):
        person_id = self.request.get('person_id')
        phantom_id = self.request.get('phantom_id')

        new_person=None
        if person_id and phantom_id:
            person=Person.get_by_id(int(person_id))
            phantom=Phantom.get_by_id(int(phantom_id))
           
            person.phantom_name=phantom
            person.put()
            new_person=person
   
        phantoms=getAllPhantoms()
        people=[]
        lonely_phantoms=[]
        for phantom in phantoms:
            possible_persons=Person.query(Person.phantom_name==phantom).fetch()
            if len(possible_persons)==0:
                lonely_phantoms.append(phantom)
            elif possible_persons[0]!=new_person:
                people.append(possible_persons[0])

        user = users.get_current_user()
        is_admin=False

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'

            if user.email() in admin_white_list:
                is_admin=True
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        


        template_values = {
                        'new_person':new_person,
                        'people':people,
                        'phantoms':lonely_phantoms,
                        'is_admin':is_admin,
                       'user': user,
                       'url': url,
                        'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))





class ResultsPage(webapp2.RequestHandler):
    """
    Class for the results page after user has entered their name.
    Each result redirects to the home page, which changes its welcome message  

    Displays:
    1. Welcome Message
    2. Phantom Option 1, with description of phantom
    3. Phantom Option 2, with description of phantom
    4. Phantom Option 3, with description of phantom
    """


    def get(self):
        """
        This fuction selects 3 phantom names based on a uniquie shuffle
        of the phantom names
        """
        first_name = self.request.get('first_name')
        last_name = self.request.get('last_name')
        print first_name,last_name
        
        
        # Figure out is the person with the first and last name exists
        # Save a new entity if not 
        
        possible_persons=Person.query(
                                    Person.first_name==first_name,
                                    Person.last_name==last_name).fetch()     
        
        user = users.get_current_user()
        user_nickname="guest"
        if user:
            user_nickname=user.nickname()


        if len(possible_persons)==0:
            person=Person(first_name=first_name,last_name=last_name,creator=user_nickname)
            person.put()
        else:
            person=possible_persons[0]


        # Get all the phantoms into an ordered list
        # 
        # I dont trust that they will be loaded from the database
        # in the same order each time so sort them by each entities key id
        all_phantoms=getAllPhantoms()

        phantoms_dict={}
        for phantom in all_phantoms:
            phantoms_dict[str(phantom.key.id())]=phantom

        unordered_phantoms=phantoms_dict.keys()
        unordered_phantoms.sort()
        ordered_phantoms = unordered_phantoms


        # Once the phantoms are in a reliable order
        # shuffle them using the person key id as a seed
        # All phantoms will always be suffled 
        # in this exact order for this peson

        random.seed(person.key.id())
        random.shuffle(ordered_phantoms)
        
        uniquely_shuffled_phantoms=ordered_phantoms
        

        # Get three phantoms from the top of this list
        # ensuring each hasnt already been allocated before

        three_phantoms=[]
        for phantom_id in uniquely_shuffled_phantoms:
            phantom=phantoms_dict[phantom_id]

            possible_persons=Person.query(
                Person.phantom_name.name==phantom.name).fetch()


            
            if (len(possible_persons)==1 and 
                    possible_persons[0].key.id()==person.key.id()):
                possible_persons=[]

            if len(possible_persons)==0 :
                three_phantoms.append(phantom)
            if len(three_phantoms)==3:
                break



        # render out page
        template_values = {
                'person':person,
                'phantoms':three_phantoms
        }
        template = JINJA_ENVIRONMENT.get_template('results.html')
        self.response.write(template.render(template_values))


class AdminPage(webapp2.RequestHandler):
    """
    Class for the admin page that is only available after the user is logged in
    
    Displays 
    1. Each users along with options to delete each one or re-assign a name
    2. An add user option
    3. Save changes button
    4. Return button
    """


    def post(self):
        """
        Page loaded after user has made a nickname choice
        """

        match_data=json.loads(str(self.request.POST.get('data')))

       
        saved_people=[]
        for match in match_data:
            possible_persons=Person.query(
                                        Person.first_name==match[0],
                                        Person.last_name==match[1]).fetch()
            phantom=None
            if match[2]!="empty":
                phantom=Phantom.get_by_id(int(match[2]))
            user = users.get_current_user()
            user_nickname="guest"
            if user:
                user_nickname=user.nickname()

            if len(possible_persons)==0:
                if match[0]!="" and match[1]!="":
                    person=Person(first_name=match[0],
                                  last_name=match[1],
                                  creator=user_nickname,
                                  phantom_name=phantom)
                    person.put()
                    saved_people.append(person)
            else:
                for possible_person in possible_persons:

                    possible_person.phantom_name=phantom
                    possible_person.put()
                    saved_people.append(possible_person)

        for possiblely_deleted_person in Person.query().fetch():
            if possiblely_deleted_person not in saved_people:
                possiblely_deleted_person.key.delete()
        
     

    def get(self):
        """
        Page loaded on first entry to site
        """
        people=Person.query().fetch()
        template_values = {
                            'saved':False,
                            'people':people,
                            'phantoms':getAllPhantoms()}

        template = JINJA_ENVIRONMENT.get_template('admin.html')
        self.response.write(template.render(template_values))



class FormPage(webapp2.RequestHandler):
    """
    Simple class to retreive user details

    Displays:
    1. First name text box
    2. Last name text box
    3. Submit button
    """

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('form.html')
        self.response.write(template.render(template_values))




app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/form', FormPage),
    ('/admin', AdminPage),
    ('/results', ResultsPage),
], debug=True)