from flask_wtf import FlaskForm
from wtforms import FormField, SubmitField, StringField, BooleanField, RadioField
from wtforms.validators import DataRequired, ValidationError, Regexp, Email
from .models import Team, TeamMember, Beer
from wtforms_alchemy import ModelForm, ModelFieldList
from app import app, logic
from datetime import datetime, timedelta

def validate_age(form, field):
    try:
        birthdate = datetime.strptime(field.data[:8], "%Y%m%d")
        age = (datetime.now() - birthdate) // timedelta(days=365.25)
        if age < 20:
            raise ValidationError("Du måste vara minst 20 år gammal för att få åka med.")
    except ValueError:
        raise ValidationError("Du måste vara minst 20 år gammal för att få åka med.")


class MemberForm(ModelForm, FlaskForm):
    class Meta:
        model = TeamMember
        csrf = False
    tickets = []
    for index,ticket in enumerate(app.config['FLUMRIDE']['ticket_types']):
        tickets.append( (index, ticket['name'] +' - ' +str(ticket['price']) + 'kr') )
    ticket_type = RadioField('Välj biljett:', choices=tickets, coerce=int)
    drinks = []
    for index,drink in enumerate(app.config['FLUMRIDE']['drink_options']):
        drinks.append( (index, drink['name']) )
    drink_option = RadioField('Välj dryck till sittningen:', choices=drinks, coerce=int)

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        member = kwargs.get('obj')
        tickets_to_del = []
        for index, ticket in self.tickets:
            if (logic.get_number_of_tickets_for_this_type_left(index) <= 0 and member and index != member.ticket_type):
                tickets_to_del.append(index)

        tickets_to_del.sort(reverse=True)
        for index in tickets_to_del:
            del self.tickets[index]

    def validate_unique_person_number(self, person_number) :
        if TeamMember.query.filter_by(person_number=person_number.data).first():
            raise ValidationError('Det finns redan en användare med detta personnummer.')

class TeamForm(ModelForm, FlaskForm):
    class Meta:
        model = Team
        csrf = False

    members = ModelFieldList(FormField(MemberForm),
                             min_entries=1, max_entries=10)
    accept_terms = BooleanField('accept_terms', default=False, validators=[DataRequired()])
    submit = SubmitField('Skicka anmälan!')

    def validate_members(self, members):

        remaining_tickets_for_type = [logic.get_number_of_tickets_for_this_type_left(ind) for ind, ticket in enumerate(app.config['FLUMRIDE']['ticket_types'])]
        team_tickets = [x.data['ticket_type'] for x in members]
        remaining_tickets_after_transaction = [left - team_tickets.count(index) for index, left in enumerate(remaining_tickets_for_type)]
        error = False
        for member in members:
            if member.data['ticket_type'] == None:
                #Don't do an .append() here since we dont want the default [not a valid choice] error to appear
                member.ticket_type.errors = ['Du glömde ange biljettyp för denna medlemen']
                error = True
                continue
            if remaining_tickets_after_transaction[member.data['ticket_type']] < 0:
                member.ticket_type.errors.append('Du har anget fler av denna biljettyp än vad som finns kvar')
                error = True
        #Verify all person_numbers are unique
        person_numbers = [x.data['person_number'] for x in members]
        duplicate_person_numbers = [x for n, x in enumerate(person_numbers) if x in person_numbers[:n]]
        if duplicate_person_numbers:
            for member in members:
                if member.data['person_number'] in duplicate_person_numbers:
                    member.person_number.errors.append('Du har med samma personnummer flera gånger')
                    error = True
        if error:
            raise ValidationError("error in input")

    def validate_name(self, name):
        if Team.query.filter_by(name=name.data).first():
            raise ValidationError('Det finns redan ett lag med detta namn.')

class BeerForm(ModelForm, FlaskForm):
    class Meta:
        model = Beer

    name = StringField('För- och efternamn', validators=[
        DataRequired()
    ])
    email = StringField('epost@din.com', validators=[
        Email()
    ])
    person_number = StringField('Personnummer', validators=[
        DataRequired(),
        Regexp("^[12]{1}[90]{1}[0-9]{6}-[0-9]{4}$",
                    message="Skriv personnummer på formatet ååååmmdd-xxxx"),
                    validate_age
        ])
    mobile_number = StringField('Mobilnummer', validators=[
        DataRequired()
    ])
    accept_terms = BooleanField('accept_terms', default=False, validators=[DataRequired()])
    submit = SubmitField('Skicka anmälan!')

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

class LoginForm(FlaskForm):
    openid = StringField('openid', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)
